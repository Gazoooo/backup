import socket
import logging
import os

class DeviceCommunicator:
    def __init__(self):
        pass
    
    def set_logger(self):
        self.logger = logging.getLogger(__name__)
    
    #returns hostname in lowercase
    # note that becasue of this, two different host with only case sensitive difference won't be distingueshd
    def get_hostname(self):
        return socket.gethostname().lower()
    
    def get_path(self, identifier):
        return os.path.expanduser(identifier)
    
    def get_os(self):
        os_name = os.name
        if os_name == 'posix':  # Linux, macOS, etc.
            return 'linux'
        elif os_name == 'nt':  # Windows
            return 'windows'
        else:
            return "unknown"