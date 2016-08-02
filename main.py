import logging
import sys
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, default_exceptions
from linux import ip_lib
from linux import iptables_manager


def make_json_app(import_name, **kwargs):
    """
    Creates a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "Err": "405: Method Not Allowed" }
    """
    def make_json_error(ex):
        response = jsonify({"Err": str(ex)})
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        return response

    wrapped_app = Flask(import_name, **kwargs)

    for code in default_exceptions.iterkeys():
        wrapped_app.errorhandler(code)(make_json_error)

    return wrapped_app


app = make_json_app(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Application started")


@app.route('/NetworkDriver.Join', methods=['POST'])
def join():
    json_data = request.get_json(force=True)
    app.logger.debug("Join JSON=%s", json_data)

    fip = json_data['FloatingIP']
    lip = json_data['LocalIP']

    # Add Fip to GW interface
    if not add_ip_to_interface(fip):
        error_message = "Add floating ip to interface Failed!"
        app.logger.error(error_message)
        raise Exception(error_message)

    # Add DNAT rule into iptables
    add_dnat_for_floating_ip(fip, lip)

    app.logger.debug("Activate response JSON=%s", "{}")
    return jsonify({})


@app.route('/NetworkDriver.Leave', methods=['POST'])
def leave():
    json_data = request.get_json(force=True)
    app.logger.debug("Leave JSON=%s", json_data)

    fip = json_data['FloatingIP']
    lip = json_data['LocalIP']

    delete_dnat_for_floating_ip(fip, lip)
    if not delete_ip_from_interface(fip):
        error_message = "Remove floating ip from interface Failed!"
        app.logger.error(error_message)
        raise Exception(error_message)

    app.logger.debug("Leave response JSON=%s", "{}")
    return jsonify({})


def add_ip_to_interface(fip):
    ip = ip_lib.IPWrapper()
    devices = ip.get_devices()
    for dev in devices:
        if dev.route.get_gateway() is not None:
            if ip.get_device_by_ip(fip) is None:
                dev.addr.add(fip)
                return True
    return False


def delete_ip_from_interface(fip):
    ip = ip_lib.IPWrapper()
    dev = ip.get_device_by_ip(fip)
    if dev is not None:
        dev.addr.delete(fip)
        return True
    return False


def add_dnat_for_floating_ip(fip, lip):
    iptable_mgmter = iptables_manager.IptablesManager(binary_name='wise2c')
    rule = '-d ' + fip + ' ! -i docker0 -j DNAT --to-destination ' + lip
    iptable_mgmter.ipv4['nat'].add_rule(chain='PREROUTING', rule=rule, comment="DNAT for floating ip")
    iptable_mgmter.apply()
    return


def delete_dnat_for_floating_ip(fip, lip):
    iptable_mgmter = iptables_manager.IptablesManager(binary_name='wise2c')
    rule = '-d ' + fip + ' ! -i docker0 -j DNAT --to-destination ' + lip
    iptable_mgmter.ipv4['nat'].remove_rule(chain='PREROUTING', rule=rule)
    iptable_mgmter.apply()
    return


def main():
    fip = '10.0.2.200'
    lip = '172.17.0.2'
    if add_ip_to_interface(fip):
        print "add ok!"

    add_dnat_for_floating_ip(fip, lip)
    print "iptable added!"

    delete_dnat_for_floating_ip(fip, lip)
    print "iptable removed!"


if __name__ == '__main__':
    main()