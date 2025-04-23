import os
import re
import shutil
import logging
import threading
from tools import get_subdirs


#class for executing tasks from view
#update_callback is a function from view to update its text area
class Executor:
    def __init__(self, subprocesshandler, update_text_callback, update_confirm_callback):
        self.logger = logging.getLogger(__name__)
        self.subprocesshandler = subprocesshandler
        self.update_text = update_text_callback
        self.update_confirm = update_confirm_callback
        self.global_error = False
        
    def set_details(self, task_infos):
        self.task_infos = task_infos

    #main function; executes every task given from the view
    def execute(self):
        self.global_error = False
        self.update_text("", clear=True)
        total_tasks = len(self.task_infos)
        for current, task in enumerate(self.task_infos, start=1):
            self.update_text(f"Now executing Task {current}/{total_tasks}...")
            match task:
                case "clean":
                    self.clean()
                case "smartphone_backup":
                    self.smartphone_backup()
                case "virus_scan":
                    self.virus_scan()
                case "health_scan":
                    self.health_scan()
                case "file_backup":
                    self.file_backup()  
        if not self.global_error:   
            self.update_text(f"Finished every task.", "success")
            self.update_confirm()        

    def clean(self):
        self.logger.info("------------Clean Task------------------")
        self.update_text("Starting cleaning...")
        try:
            clean_paths = self.task_infos["clean"]
            for dir in clean_paths:
                #self.logger.debug(f"Now removing {get_num_files(dir)} files in '{dir}'...")
                subs = get_subdirs(dir)
                for sub in subs:
                    result = self.dvc.delete(sub)
                #self.logger.debug(f"Kept {get_num_files(dir)} files in '{dir}'.")
            self.logger.info("Cleaning ended successfull")
            self.update_text("Cleaning ended successfull")
        except Exception as e:
            self.global_error = True
            self.logger.error(f"Cleaning: {e}")
            self.update_text("An error occured on the 'Cleaning'-Task. See 'Task-Log.log' for detailed information.", "error")

    #backups smartphone using iTunes
    def smartphone_backup(self):
        return "Not implemented"
        #os.startfile("C:\Program Files\iTunes\iTunes.exe")
        #TODO: pyautogui

    #scans using GDATA Antivirus CLI
    def virus_scan(self):
        return "not implemented"
        self.logger.info("Starting virus scan...")
        self.update_text("Starting virus scan...")
        try:
            gdata_cmd = r"C:\Program Files (x86)\G DATA\AntiVirus\AVK\avkcmd.exe"
            #process = subprocess.run([gdata_cmd, "/scan:C:"], check=True)
            self.logger.info("Virus scan ended successfull")
            self.update_text("Virus scan ended successfull")
        except Exception as e:
            self.logger.error(f"Virus scan: {e}")
            self.update_text("An error occured on the 'virus_scan'-Task. See 'Log.log' for detailed information.")

    #scans windows devices using DISM and sfc
    #requires admin privileges
    def health_scan(self):
        return "not implemented"
        self.update_text("Starting health scan...")
        try:
            # Run System File Checker (sfc)
            self.logger.info("Running System File Checker (sfc /scannow)...")
            #process1 = subprocess.run(["sfc", "/scannow"], check=True)
            # Run DISM to scan for component store corruption
            self.logger.info("Running DISM /Online /Cleanup-Image /ScanHealth...")
            #process2 = subprocess.run(["dism", "/online", "/cleanup-image", "/scanhealth"], check=True)
            # Run DISM to check if any corruption is repairable
            self.logger.info("Running DISM /Online /Cleanup-Image /CheckHealth...")
            #process3 = subprocess.run(["dism", "/online", "/cleanup-image", "/checkhealth"], check=True)
            #Optionally, repair corruption if detected
            self.logger.info("Running DISM /Online /Cleanup-Image /RestoreHealth...")
            #process4 = subprocess.run(["dism", "/online", "/cleanup-image", "/restorehealth"], check=True)

            self.logger.info("System checks completed successfully.")
            self.update_text("System checks completed successfully.")
        except Exception as e:
            self.logger.error(f"Health-scan: {e}")
            self.update_text("An error occured on the 'health-scan'-Task. See 'Log.log' for detailed information.")

    def file_backup(self):
        self.update_text("Starting file backup...")
        dest_dir = self.task_infos["file_backup"]["dstPath"]
        backup_paths = self.task_infos["file_backup"]["backupPaths"]
        deletable_dirs = self.task_infos["file_backup"]["to_delete"]
        #print(deletable_dirs)
        try:
            #delete old stuff
            if len(deletable_dirs) != 0:
                for dir in deletable_dirs:
                    result = self.subprocesshandler.delete(dir)
                
            #make new backup
            total_dirs_toBackup = len(backup_paths)
            for dirNum, dir in enumerate(backup_paths):
                
                #show progress
                with self.subprocesshandler.copy(dir, dest_dir) as process:
                    total_files = sum(len(files) for _, _, files in os.walk(dir))
                    copied_files = 0
                    last_percent = -1 
                    stdout_line_count = 0

                    for line in process.stdout:
                        #stdout_line_count += 1 #counter to only print some things
                        #print(stdout_line_count)
                        if re.search(r'\t[A-Z]:\\.*', line): #robocopy: begins to copy new file
                            copied_files += 1
                        if '%' in line:
                            #copied + total files important to calculate under robocopy (windows)
                            percent = self.subprocesshandler.parse_progress(line, copied_files, total_files) 
                            #if stdout_line_count % 1000 == 0:
                            if last_percent != percent:
                                last_percent = percent
                                self.update_text(f"Copying: {percent:.2f}% (Directory: {dirNum+1}/{total_dirs_toBackup})", update=True)
                    for line in process.stderr:
                        self.logger.error("copy:", line.strip())
                        
                    return_code = process.wait()
                    if return_code != 0:
                        self.logger.warning(f"Returncode is {return_code} (!= 0).")
                                
            self.logger.info("File Backup ended successfull")
            self.update_text(f"File Backup ended successfull", "success")
        
        except Exception as e:
            self.global_error = True
            self.logger.error(f"Backuping: {e}")
            self.update_text("An error occured on the 'file_backup'-Task. See 'Task-Log.log' for detailed information.", "error")
        

    #starts execution in new thread to keep GUI responsive
    def start(self):
        executor_thread = threading.Thread(target=self.execute)
        executor_thread.start()
        