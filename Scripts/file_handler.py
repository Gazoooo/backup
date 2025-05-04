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
        basePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = Path(basePath).joinpath("config.yaml")
        self.log_path =Path(basePath).joinpath("Task-Log.log")

        self.BACKUP_LIMIT = 3
        self.config_data = ""
    
    # ------------- YAML specific -----------------------------

    def parse_yaml(self):
        """Parses the configuration YAML file and stores it in self.config_data.
        Creates it as a dict if not exists. """
        try:
            if not os.path.isfile(self.config_path):
                with open(self.config_path, "a") as file:
                    yaml.dump({"hosts_map": []}, file)
            with open(self.config_path, "r") as file:
                self.config_data = yaml.safe_load(file)
        except Exception as e:
            print(e)
            self.logger.error("Couldn't parse yaml.")
    
    def search_user(self):
        """Searches for the user in the loaded config data.

        Returns:
            bool: True if user is found, False otherwise.
        """
        self.userDict = None
        if not isinstance(self.config_data, dict):
            self.logger.error("Error at the 'config.yaml' file! Delete the file to fix this.")
            exit()
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
        self.destPaths_list = self.userDict['paths']['dest_paths']
        self.destPath = self.userDict['info']['last_selected_dest']
        self.info_dict = self.userDict['info']
        self.backupPaths_list = self.userDict['paths']['backup_paths']
        
        return [self.info_dict, self.backupPaths_list, self.destPaths_list]

    def add_Host(self):
        """Adds a new host to the config data and writes it to the YAML file."""
        self.logger.debug(f"Adding new host entry for '{self.hostname}.")
        new_host = {
            "hostname": self.hostname,
            "info": {
                "last_selected_dest": self.norm(self.userPath),
                "mac": "not used", 
                "name": "not used"
            },
            "paths": {
                "backup_paths": [],
                "clean_paths": [],
                "dest_paths": [self.norm(self.userPath)]
            }
        }

        self.userDict = new_host
        if len(self.config_data['hosts_map']) > 0:
            self.userIndex = self.config_data['hosts_map'][-1]
        else:
            self.userIndex = 0
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
            if isinstance(value, str):
                value = self.norm(value) #only write UNIX like paths to yaml
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
    
    def get_yamlItem(self, key_path, index):
        """
        helper method to reconstruct absolute path from display path with '...'"""
        keys = key_path.split(".")
        ref = self.userDict
        for key in keys[:-1]:
            ref = ref[key]
            last_key = keys[-1]
        return ref[last_key][index]

    def write_yaml(self):
        """Writes the config data to the YAML file."""
        try:
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config_data, f)
            self.logger.info(f"Config written to '{self.config_path}'.")
        except Exception as e:
            self.logger.error(f"write_yaml: {e}")
            raise e

    # --------------- File related (Paths, Logging, ...) -------------------------

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

    def backup_alreadyExists(self):
        """
        Reports if backup from today already exists.
        
        Returns:
        bool: True if yes, else false
        """
        self.backup_path = Path(self.destPath).joinpath(self.hostname, f"backup_{self.get_date()}")
        if os.path.isdir(self.backup_path):
            return True
        else:
            return False

    def create_backupPath(self):
        """Creates a backup directory path based on current date.

        Returns:
            str: Full path to the backup directory.

        Raises:
            Exception: If directory creation fails.
        """
        self.backup_path = Path(self.destPath).joinpath(self.hostname, f"backup_{self.get_date()}")
        try:
            os.makedirs(self.backup_path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"create_backup: {e}")
            raise e
        return self.backup_path

    def check_old_backups(self, prefix):
        """Checks for outdated backup folders to delete.

        Args:
            prefix (str): Prefix of the backup folders.

        Returns:
            list: List of paths to be deleted.
        """
        path = Path(self.destPath).joinpath(self.hostname)
        self.logger.info(f"Now checking for old stuff to delete in '{path}' ...")
        self.logger.debug(f"delete-prefix: {prefix}; num backups: {self.get_num_files(path)}")
        to_delete_dirs = []
        today = self.get_date()

        for name in os.listdir(path):
            #print(f"found in dir: {name}")
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
                    pass
            elif os.path.isfile(full_path):
                self.logger.warning(f"Standalone file found in '{path}'. There shouldn't be any.")

        to_delete_dirs.sort(reverse=True, key=lambda x: x[0])
        to_delete_dirs = [path for _, path in to_delete_dirs[self.BACKUP_LIMIT:]]
        self.logger.info(f"{len(to_delete_dirs)} dirs to be deleted saved in a list; will delete it short after.")

        return to_delete_dirs

    def norm(self, paths):
        """Normalizes file paths to UNIX Style. ("/")

        Args:
            paths (Union[str, list]): A single path or a list of paths.

        Returns:
            str: Normalized path.

        Raises:
            TypeError: If input is not str or list of str.
        """
        if isinstance(paths, str):
            return paths.replace("\\", "/")
        elif isinstance(paths, list):
            return [p.replace("\\", "/") for p in paths]
        else:
            raise TypeError("norm: Input must be a string or a list of strings")

    def visualize_path(self, path, short=False):
        """
        Normalize paths depending on operating system (uses '/' on Linux/macOS, '\' on Windows)

        Args:
            paths (str): A single path.
            short (bool): If True, shorten the path by only showing the first 2 and last 2 parts.

        Returns:
            Union[str, list]: Normalized path(s).

        Raises:
            TypeError: If input is not str or list of str.
        """
        path = os.path.normpath(path)

        front = 3
        back = 2
        if short:
            parts = path.split(os.sep)
            #print(path, parts)
            if len(parts) > front+back and len(path) > front+back:
                path = os.sep.join(parts[:front]) + os.sep + "..." + os.sep + os.sep.join(parts[-back:])
            
        return path

    def get_size(self, path):
        """Returns the size of a file or directory recursively.

        Args:
            path (str): Path to the file or directory.

        Returns:
            int: Size in GB.
        """
        if os.path.isfile(path):
            total_size = os.path.getsize(path)
        elif os.path.isdir(path):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except FileNotFoundError:
                        self.logger.info(f"get_size(): File not found (skipped): {fp}")
                    except PermissionError:
                        self.logger.info(f"get_size(): Permission denied (skipped): {fp}")
        else:
            raise ValueError(f"Path '{path}' is neither a file nor a directory.")
        return total_size / (1024 * 1024 * 1024)  # Convert to GB

    # ------------------------------ Other -----------------------------
    def set_callback(self, callback):
        """Sets the callback function for updating text."""
        self.update_text = callback