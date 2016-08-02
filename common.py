import eventlet
import os
import six
import errno
import signal
from oslo_log import log
from oslo_utils import excutils
from _i18n import _, _LI
from eventlet.green import subprocess
from oslo_config import cfg

LOG = log.getLogger(__name__)
_IS_IPV6_ENABLED = None

# Default network MTU value when not configured
DEFAULT_NETWORK_MTU = 1500
IPV6_MIN_MTU = 1280
SYNCHRONIZED_PREFIX = 'wise2c-'
TAP_DEVICE_PREFIX = 'tap'
IP_VERSION_4 = 4
IP_VERSION_6 = 6
IPv4_ANY = '0.0.0.0/0'
IPv6_ANY = '::/0'
IP_ANY = {IP_VERSION_4: IPv4_ANY, IP_VERSION_6: IPv6_ANY}
# Linux interface max length
DEVICE_NAME_MAX_LEN = 15

PROCESS_MONITOR_OPTS = [
    cfg.StrOpt('check_child_processes_action', default='respawn',
               choices=['respawn', 'exit'],
               help=_('Action to be executed when a child process dies')),
    cfg.IntOpt('check_child_processes_interval', default=60,
               help=_('Interval between checks of child process liveness '
                      '(seconds), use 0 to disable')),
]

def wait_until_true(predicate, timeout=60, sleep=1, exception=None):
    """
    Wait until callable predicate is evaluated as True

    :param predicate: Callable deciding whether waiting should continue.
    Best practice is to instantiate predicate with functools.partial()
    :param timeout: Timeout in seconds how long should function wait.
    :param sleep: Polling interval for results in seconds.
    :param exception: Exception class for eventlet.Timeout.
    (see doc for eventlet.Timeout for more information)
    """
    with eventlet.timeout.Timeout(timeout, exception):
        while not predicate():
            eventlet.sleep(sleep)


def ensure_dir(dir_path):
    """Ensure a directory with 755 permissions mode."""
    try:
        os.makedirs(dir_path, 0o755)
    except OSError as e:
        # If the directory already existed, don't raise the error.
        if e.errno != errno.EEXIST:
            raise


def safe_decode_utf8(s):
    if six.PY3 and isinstance(s, bytes):
        return s.decode('utf-8', 'surrogateescape')
    return s


def is_enabled():
    global _IS_IPV6_ENABLED

    if _IS_IPV6_ENABLED is None:
        disabled_ipv6_path = "/proc/sys/net/ipv6/conf/default/disable_ipv6"
        if os.path.exists(disabled_ipv6_path):
            with open(disabled_ipv6_path, 'r') as f:
                disabled = f.read().strip()
            _IS_IPV6_ENABLED = disabled == "0"
        else:
            _IS_IPV6_ENABLED = False
        if not _IS_IPV6_ENABLED:
            LOG.info(_LI("IPv6 is not enabled on this system."))
    return _IS_IPV6_ENABLED


def _subprocess_setup():
    # Python installs a SIGPIPE handler by default. This is usually not what
    # non-Python subprocesses expect.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)


def subprocess_popen(args, stdin=None, stdout=None, stderr=None, shell=False,
                         env=None, preexec_fn=_subprocess_setup, close_fds=True):

    return subprocess.Popen(args, shell=shell, stdin=stdin, stdout=stdout,
                            stderr=stderr, preexec_fn=preexec_fn,
                            close_fds=close_fds, env=env)


class Wise2cException(Exception):
    """Base Wise2c Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(Wise2cException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(Wise2cException, self).__init__(self.message)

    if six.PY2:
        def __unicode__(self):
            return unicode(self.msg)

    def __str__(self):
        return self.msg

    def use_fatal_exceptions(self):
        return False


class IpTablesApplyException(Wise2cException):
    def __init__(self, message=None):
        self.message = message
        super(IpTablesApplyException, self).__init__()


class FailToDropPrivilegesExit(SystemExit):
    """Exit exception raised when a drop privileges action fails."""
    code = 99

class DeviceNotFoundError(Wise2cException):
    message = _("Device '%(device_name)s' does not exist.")

class NetworkVxlanPortRangeError(Wise2cException):
    message = _("Invalid network VXLAN port range: '%(vxlan_range)s'.")

class BridgeDoesNotExist(Wise2cException):
    message = _("Bridge %(bridge)s does not exist.")


def register_process_monitor_opts(conf):
    conf.register_opts(PROCESS_MONITOR_OPTS, 'AGENT')


def get_root_helper(conf):
    return ""