import socket
import logging
import os

class DeviceCommunicator:
    """
    A class to handle device-related operations such as retrieving the hostname,
    determining the operating system, and managing file paths.
    """

    def __init__(self):
        """
        Initializes the DeviceCommunicator instance.
        """
        pass
    
    def set_logger(self):
        """
        Sets up a logger for the DeviceCommunicator instance.
        """
        self.logger = logging.getLogger(__name__)
    
    def get_hostname(self):
        """
        Retrieves the hostname of the current device in lowercase.

        Note:
            Hostnames that differ only in case will not be distinguished.

        Returns:
            str: The hostname of the device in lowercase letters.
        """
        return socket.gethostname().lower()
    
    def get_path(self, identifier):
        """
        Expands and returns the user-specific path for the given identifier.

        Args:
            identifier (str): A string representing the path to be expanded.

        Returns:
            str: The expanded user-specific path.
        """
        return os.path.expanduser(identifier)
    
    def get_os(self):
        """
        Determines the operating system of the current device.

        Returns:
            str: The name of the operating system ('linux', 'windows', or 'unknown').
        """
        os_name = os.name
        if os_name == 'posix':  # Linux, macOS, etc.
            return 'linux'
        elif os_name == 'nt':  # Windows
            return 'windows'
        else:
            return "unknown"