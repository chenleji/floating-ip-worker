import logging
import sys
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException, default_exceptions
from linux import ip_lib


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
    #ip = ip_lib.IPWrapper()
    #route =

    # Add DNAT rule into iptables


    json_response = {
        "InterfaceName": {
            "SrcName": None,
            "DstPrefix": None,
        }
    }
    app.logger.debug("Activate response JSON=%s", json_response)
    return jsonify(json_response)


@app.route('/NetworkDriver.Leave', methods=['POST'])
def leave():
    json_data = request.get_json(force=True)
    app.logger.debug("Leave JSON=%s", json_data)

    ep_id = json_data["EndpointID"]
    app.logger.info("Leaving endpoint %s", ep_id)

    app.logger.debug("Leave response JSON=%s", "{}")
    return jsonify({})


def main():
    ip = ip_lib.IPWrapper()
    devices = ip.get_devices()
    print dir(devices)

if __name__ == '__main__':
    main()