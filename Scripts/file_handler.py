from datetime import datetime
import logging
import os
import yaml
from dateutil import parser


class FileHandler():
    def __init__(self, hostname, userPath):
        self.hostname = hostname
        self.userPath = userPath
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
        self.log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Task-Log.log")
        
        self.BACKUP_LIMIT = 3
        self.config_data = ""
              
        
    #-------------yaml specific-----------------------------
    #parses yaml; should be called first
    def parse_yaml(self):
        try:
            with open(self.config_path, "r") as file:
                self.config_data = yaml.safe_load(file)
        except Exception:
            print("Couldn't parse yaml.")
        
    def search_user(self):
        # search for correct host and returns true or false
        self.userDict = None
        for idx, host_dict in enumerate(self.config_data['hosts_map']):
            if host_dict['hostname'] == self.hostname:
                self.userDict = host_dict
                self.userIndex = idx
                return True 
        if self.userDict == None:
            return False
    
    #parses yaml and returns right dicts for specific user
    def get_userContent(self):
        self.destPaths_list = self.norm(self.userDict['paths']['dest_paths'])
        self.destPath = self.norm(self.userDict['info']['last_selected_dest'])
        self.info_dict = self.userDict['info']
        self.backupPaths_list = self.norm(self.userDict['paths']['backup_paths'])
        
        return [self.info_dict, self.backupPaths_list, self.destPaths_list]
    
    def add_Host(self):
        new_host = {
        "hostname": self.hostname,
        "info": 
            {
                "last_selected_dest": "None",
                "mac": "not used", 
                "name": "not used"
             }
        ,
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
        

    #Updates a existing Key-Pfad in self.userDict
    #key_path dot-separated: z.B. "paths.backup_paths"
    # value: new value or valeu to delete
    def update_yaml(self, key_path, value, delete=False):
        try:
            keys = key_path.split(".")
            ref = self.userDict

            #navigate to right position
            for key in keys[:-1]:
                ref = ref[key]
            
            #last key (to be updated)
            last_key = keys[-1]
            if isinstance(ref.get(last_key), list):
                if not delete:
                    if value not in ref[last_key]:
                        ref[last_key].append(value)
                    else:
                        self.logger.info(f"Value already in yaml list. Ignoring")
                        
                else:
                    if value in ref[last_key]:
                        ref[last_key].remove(value)
                    else:
                        raise ValueError(f"Value '{value}' not in list!")
                    
            else: #simple string
                if not delete:
                    ref[last_key] = value
                else:
                    ref.pop(last_key, None)  # delete also when not exists
        except Exception as e:
            self.logger.error(f"update_yaml: {e}")
            raise e
                
        _ = self.get_userContent() #also update own vars by calling this method
        
    def write_yaml(self):
        try:
            with open(self.config_path, "w") as f:
                yaml.safe_dump(self.config_data, f)
            self.logger.info(f"Config written to '{self.config_path}.")
        except Exception as e:
            self.logger.error(f"write_yaml: {e}")
            raise e
   
    #---------------paths-------------------------
    #get todays date and returns it as string
    #standard is ISO 8601
    def get_date(self, format="%Y-%m-%d"):
        timestamp = datetime.now()
        formatted_timestamp = timestamp.strftime(format)
        return formatted_timestamp

    #gets num of files+dirs in a parent dir
    #can specify that only specific files+dirs should be counted
    def get_num_files(self, dir, prefix=None):
        all = os.listdir(dir)
        if prefix is None:
            return len(all)
        else:
            return len([f for f in all if f.startswith(prefix)])
    
    #creates and configs the log for the whole program
    #does nothing when file already exists
    def setup_logger(self):
        try:
            with open(self.log_path, "a") as file:
                file.write(f"-------------------SESSION_{self.get_date(format="%Y-%m-%d %H:%M:%S")}--------------------------\n")
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
                
    #creates the right dir to backup in for "executor"
    def create_backupPath(self):
        self.backup_path = os.path.join(self.destPath, self.hostname, f"backup_{self.get_date()}")
        try:
            os.makedirs(self.backup_path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"create_backup: {e}.")
            raise e
        
        return self.backup_path

    #constructs absolute paths in case the user entered relative ones
    #and norms them
    def construct_absolute_paths(self, pathList, task=None):
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

        
    #checks witch folders+files in userpath to delete 
    #keeps the <=LIMIT newest backups + only newest .log
    #returns the paths in a list
    def check_deletable(self, prefix):
        path = os.path.join(self.destPath, self.hostname)
        self.logger.info(f"Now checking for old stuff to delete in '{path}' ...")
        self.logger.debug(f"delete-prefix: {prefix}; num backups: {self.get_num_files(path)}")
        to_delete_dirs = []
        today = self.get_date()
        
        for name in os.listdir(path):
            if name.endswith(".log"): #ignore logging files
                continue
            full_path = os.path.join(path, name)
            try:
                date = parser.parse(name, fuzzy=True).date()
            except Exception as e: #ignore names without dates
                self.logger.warning(f"'{name}' has no date in it.") 
            
            if name.startswith(prefix) and os.path.isdir(full_path):
                to_delete_dirs.append((date, full_path))
                if date.strftime("%Y-%m-%d") == today:
                    self.logger.info(f"Backup from today already exists. Maybe it will be overridden...")
            elif os.path.isfile(full_path):
                self.logger.warning(f"Standalone file found in '{path}'. There shouldn't be any.")

        to_delete_dirs.sort(reverse=True, key=lambda x: x[0])
        to_delete_dirs = [path for _, path in to_delete_dirs[self.BACKUP_LIMIT:]]   
        self.logger.info(f"{len(to_delete_dirs)} dirs to be deleted saved in a list; will delete it short after.")

        return to_delete_dirs

    #transforms a path list/single path to windows/linux paths depending on host
    #linux: \
    #windows: /
    def norm(self, paths):
        #self.logger.debug(f"Norming paths: {paths}...")
        if isinstance(paths, str):
            return os.path.normpath(paths)
        elif isinstance(paths, list):
            return [os.path.normpath(p) for p in paths]
        else:
            raise TypeError("norm: Input must be a string or a list of strings")
