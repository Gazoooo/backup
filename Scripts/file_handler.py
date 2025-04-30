from datetime import datetime
import logging
import os
from pathlib import Path
import yaml
from dateutil import parser


class FileHandler():
    """Handles configuration and backup tasks for a specific user and host."""
    
    def __init__(self, hostname, userPath):
        """Initializes the FileHandler.

        Args:
            hostname (str): The name of the host machine.
            userPath (str): The path provided by the user for destination or backup.
            update_text_callback: Function to update the text area in the view.
        """
        self.hostname = hostname
        self.userPath = userPath
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        self.log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Task-Log.log")

        self.BACKUP_LIMIT = 3
        self.config_data = ""
    
    # ------------- YAML specific -----------------------------

    def parse_yaml(self):
        """Parses the configuration YAML file and stores it in self.config_data."""
        try:
            with open(self.config_path, "r") as file:
                self.config_data = yaml.safe_load(file)
        except Exception:
            print("Couldn't parse yaml.")
    
    def search_user(self):
        """Searches for the user in the loaded config data.

        Returns:
            bool: True if user is found, False otherwise.
        """
        self.userDict = None
        for idx, host_dict in enumerate(self.config_data['hosts_map']):
            if host_dict['hostname'] == self.hostname:
                self.userDict = host_dict
                self.userIndex = idx
                return True 
        return False
    
    def get_userContent(self):
        """Extracts user-specific paths and information.

        Returns:
            list: [info_dict, backupPaths_list, destPaths_list]
        """
        self.destPaths_list = self.norm(self.userDict['paths']['dest_paths'])
        self.destPath = self.norm(self.userDict['info']['last_selected_dest'])
        self.info_dict = self.userDict['info']
        self.backupPaths_list = self.norm(self.userDict['paths']['backup_paths'])
        
        return [self.info_dict, self.backupPaths_list, self.destPaths_list]

    def add_Host(self):
        """Adds a new host to the config data and writes it to the YAML file."""
        new_host = {
            "hostname": self.hostname,
            "info": {
                "last_selected_dest": "None",
                "mac": "not used", 
                "name": "not used"
            },
            "paths": {
                "backup_paths": [],
                "clean_paths": [],
                "dest_paths": [self.userPath]
            }
        }

        self.userDict = new_host
        self.userIndex = self.config_data['hosts_map'][-1]
        self.config_data['hosts_map'].append(new_host)
        self.write_yaml()

    def update_yaml(self, key_path, value, delete=False):
        """Updates or deletes a value in the user dictionary.

        Args:
            key_path (str): Dot-separated path to the key to update.
            value (Any): Value to update or delete.
            delete (bool): Whether to delete the value.

        Raises:
            Exception: If update or deletion fails.
        """
        try:
            keys = key_path.split(".")
            ref = self.userDict
            for key in keys[:-1]:
                ref = ref[key]
            last_key = keys[-1]
            if isinstance(ref.get(last_key), list):
                if not delete:
                    if value not in ref[last_key]:
                        ref[last_key].append(value)
                    else:
                        self.logger.info("Value already in yaml list. Ignoring")
                else:
                    if value in ref[last_key]:
                        ref[last_key].remove(value)
                    else:
                        raise ValueError(f"Value '{value}' not in list!")
            else:
                if not delete:
                    ref[last_key] = value
                else:
                    ref.pop(last_key, None)
        except Exception as e:
            self.logger.error(f"update_yaml: {e}")
            raise e
        _ = self.get_userContent()
    
    def write_yaml(self):
        """Writes the config data to the YAML file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config_data, f)
            self.logger.info(f"Config written to '{self.config_path}'.")
        except Exception as e:
            self.logger.error(f"write_yaml: {e}")
            raise e

    # --------------- Path and Logging -------------------------

    def get_date(self, format="%Y-%m-%d"):
        """Returns current date as string.

        Args:
            format (str): Format string. Defaults to ISO 8601.

        Returns:
            str: Formatted current date.
        """
        timestamp = datetime.now()
        return timestamp.strftime(format)

    def get_num_files(self, dir, prefix=None):
        """Counts files and directories in a given path.

        Args:
            dir (str): Directory path.
            prefix (str, optional): Only count entries starting with this prefix.

        Returns:
            int: Number of matching files/directories.
        """
        all = os.listdir(dir)
        if prefix is None:
            return len(all)
        return len([f for f in all if f.startswith(prefix)])

    def setup_logger(self):
        """Sets up the logger and adds a session header to the log file."""
        try:
            with open(self.log_path, "a") as file:
                file.write(f"-------------------SESSION_{self.get_date(format='%Y-%m-%d %H:%M:%S')}--------------------------\n")
        except Exception as e:
            raise e

        logging.basicConfig(
            level=logging.DEBUG,
            format='[%(levelname)s - %(name)s] %(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_backupPath(self):
        """Creates a backup directory path based on current date.

        Returns:
            str: Full path to the backup directory.

        Raises:
            Exception: If directory creation fails.
        """
        self.backup_path = os.path.join(self.destPath, self.hostname, f"backup_{self.get_date()}")
        try:
            os.makedirs(self.backup_path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"create_backup: {e}")
            raise e
        return self.backup_path

    def construct_absolute_paths(self, pathList, task=None):
        """Normalizes and constructs absolute paths from given paths.

        Args:
            pathList (list): List of relative or absolute paths.
            task (str, optional): Not used currently.

        Returns:
            list: List of absolute paths.

        Raises:
            Exception: If construction fails.
        """
        user_path = os.path.expanduser("~")
        try:
            absolute_paths = [
                path if os.path.isabs(path) else os.path.join(user_path, path)
                for path in pathList
            ]
            self.norm(absolute_paths)
            return absolute_paths
        except Exception as e:
            self.logger.error(f"construct_absolute_paths: {e}")
            raise e

    def check_deletable(self, prefix):
        """Checks for outdated backup folders to delete.

        Args:
            prefix (str): Prefix of the backup folders.

        Returns:
            list: List of paths to be deleted.
        """
        path = os.path.join(self.destPath, self.hostname)
        self.logger.info(f"Now checking for old stuff to delete in '{path}' ...")
        self.logger.debug(f"delete-prefix: {prefix}; num backups: {self.get_num_files(path)}")
        to_delete_dirs = []
        today = self.get_date()

        for name in os.listdir(path):
            print(name)
            if name.endswith(".log"): #ignore logs
                continue
            full_path = os.path.join(path, name)
            try:
                date = parser.parse(name, fuzzy=True).date()
            except Exception:
                self.logger.warning(f"'{name}' has no date in it.")
                continue

            if name.startswith(prefix) and os.path.isdir(full_path):
                to_delete_dirs.append((date, full_path))
                if date.strftime("%Y-%m-%d") == today and any(Path(full_path).iterdir()): # ignore if newly created
                    self.update_text(f"Backup from today already exists. Maybe it will be overridden...", "warning")
                    self.logger.warning(f"Backup from today already exists. Maybe it will be overridden...")
            elif os.path.isfile(full_path):
                self.logger.warning(f"Standalone file found in '{path}'. There shouldn't be any.")

        to_delete_dirs.sort(reverse=True, key=lambda x: x[0])
        to_delete_dirs = [path for _, path in to_delete_dirs[self.BACKUP_LIMIT:]]
        self.logger.info(f"{len(to_delete_dirs)} dirs to be deleted saved in a list; will delete it short after.")

        return to_delete_dirs

    def norm(self, paths):
        """Normalizes file paths according to OS.

        Args:
            paths (Union[str, list]): A single path or a list of paths.

        Returns:
            Union[str, list]: Normalized path(s).

        Raises:
            TypeError: If input is not str or list of str.
        """
        if isinstance(paths, str):
            return os.path.normpath(paths)
        elif isinstance(paths, list):
            return [os.path.normpath(p) for p in paths]
        else:
            raise TypeError("norm: Input must be a string or a list of strings")


    # ------------------------------ Other -----------------------------
    def set_callback(self, callback):
        """Sets the callback function for updating text."""
        self.update_text = callback