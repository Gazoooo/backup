import os
import re
import shutil
import logging
import threading
from tools import get_subdirs


# class for executing tasks from view
# update_callback is a function from view to update its text area
class Executor:
    def __init__(self, subprocesshandler, update_text_callback, update_rdy_callback):
        """Initializes the Executor.

        Args:
            subprocesshandler: Handler for subprocess-based operations like copy and delete.
            update_text_callback: Function to update the text area in the view.
            update_rdy_callback: Function to signal task execution in the view.
        """
        self.logger = logging.getLogger(__name__)
        self.subprocesshandler = subprocesshandler
        self.update_text = update_text_callback
        self.update_rdy = update_rdy_callback
        self.global_error = False
        self.stop = False
        
    def set_details(self, task_infos):
        """Sets task-specific details for the executor.

        Args:
            task_infos (dict): Dictionary containing task names as keys and corresponding data as values.
        """
        self.task_infos = task_infos

    def execute(self):
        """Executes all tasks provided in `task_infos` sequentially."""
        try:
            self.global_error = False
            total_tasks = len(self.task_infos)
            for current, task in enumerate(self.task_infos, start=1):
                if self.stop:
                    return
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
                        
            if self.stop:
                self.update_text("Stopped all tasks.", "success")
                self.stop = False
                
            elif not self.global_error:   
                self.update_text(f"Finished every task.", "success")
                
            self.update_rdy() 
            self.globsal_error = False
            
        except Exception as e:    
            print(f"execute(): {e}")   

    def clean(self):
        """Deletes the contents of directories specified in `task_infos["clean"]`."""
        self.update_text("Starting cleaning...")
        clean_paths = self.task_infos["clean"]["cleanPaths"]
        old_backup_paths = self.task_infos["clean"]["oldBackups"]
        try:
            #delete old backup data
            self.update_text(f"Deleting {len(old_backup_paths)} old backups...")
            if len(old_backup_paths) != 0:
                for dir in old_backup_paths:
                    result = self.subprocesshandler.delete(dir)
            
            """ 
            #clean pc
            for dir in clean_paths:
                subs = get_subdirs(dir)
                for sub in subs:
                    result = self.dvc.delete(sub)
            """  
            
            self.logger.info("Cleaning ended successfull")
            self.update_text("Cleaning ended successfull", "success")
        except Exception as e:
            self.global_error = True
            self.logger.error(f"Cleaning: {e}")
            self.update_text("An error occured on the 'Cleaning'-Task. See 'Task-Log.log' for detailed information.", "error")

    def smartphone_backup(self):
        """Backs up the smartphone using iTunes (currently not implemented).

        Returns:
            str: Status message.
        """
        return "Not implemented"
        # os.startfile("C:\Program Files\iTunes\iTunes.exe")
        # TODO: pyautogui

    def virus_scan(self):
        """Scans the system using GDATA Antivirus CLI (currently not implemented).

        Returns:
            str: Status message.
        """
        return "not implemented"
        self.logger.info("Starting virus scan...")
        self.update_text("Starting virus scan...")
        try:
            gdata_cmd = r"C:\Program Files (x86)\G DATA\AntiVirus\AVK\avkcmd.exe"
            # process = subprocess.run([gdata_cmd, "/scan:C:"], check=True)
            self.logger.info("Virus scan ended successfull")
            self.update_text("Virus scan ended successfull")
        except Exception as e:
            self.logger.error(f"Virus scan: {e}")
            self.update_text("An error occured on the 'virus_scan'-Task. See 'Log.log' for detailed information.")

    def health_scan(self):
        """Performs a system health scan using SFC and DISM (currently not implemented).

        Returns:
            str: Status message.
        """
        return "not implemented"
        self.update_text("Starting health scan...")
        try:
            # Run System File Checker (sfc)
            self.logger.info("Running System File Checker (sfc /scannow)...")
            # process1 = subprocess.run(["sfc", "/scannow"], check=True)
            # Run DISM to scan for component store corruption
            self.logger.info("Running DISM /Online /Cleanup-Image /ScanHealth...")
            # process2 = subprocess.run(["dism", "/online", "/cleanup-image", "/scanhealth"], check=True)
            self.logger.info("Running DISM /Online /Cleanup-Image /CheckHealth...")
            # process3 = subprocess.run(["dism", "/online", "/cleanup-image", "/checkhealth"], check=True)
            self.logger.info("Running DISM /Online /Cleanup-Image /RestoreHealth...")
            # process4 = subprocess.run(["dism", "/online", "/cleanup-image", "/restorehealth"], check=True)

            self.logger.info("System checks completed successfully.")
            self.update_text("System checks completed successfully.")
        except Exception as e:
            self.logger.error(f"Health-scan: {e}")
            self.update_text("An error occured on the 'health-scan'-Task. See 'Log.log' for detailed information.")

    def file_backup(self):
        """Performs a file backup operation.

        Deletes old backup data, then copies new data from `backupPaths` to `dstPath`.
        Shows live progress during copying.
        """
        self.update_text("Starting file backup...")
        dest_dir = self.task_infos["file_backup"]["dstPath"]
        backup_paths = self.task_infos["file_backup"]["backupPaths"]
        try:  
            # make new backup
            total_dirs_toBackup = len(backup_paths)
            self.update_text("---")
            for dirNum, dir in enumerate(backup_paths):
                if self.stop:
                    return
                with self.subprocesshandler.copy(dir, dest_dir) as process:
                    total_files = sum(len(files) for _, _, files in os.walk(dir))
                    copied_files = 0
                    last_percent = -1 

                    for line in process.stdout:
                        #print(line)
                        if re.search(r'\t[A-Z]:\\.*', line):  # robocopy: begins to copy new file
                            copied_files += 1
                        if '%' in line:
                            percent = self.subprocesshandler.parse_progress(line, copied_files, total_files)
                            if last_percent != percent:
                                last_percent = percent
                                self.update_text(f"Copying: {percent:.2f}% (Directory: {dirNum+1}/{total_dirs_toBackup})", update=True)
                    for line in process.stderr:
                        self.logger.error(f"copy: {line.strip()}")

                    return_code = process.wait()
                    self.logger.debug(f"Returncode is {return_code}.")
                    msg = self.subprocesshandler.get_exitcode("backup", return_code)
                    if msg:
                        self.logger.debug(f"=> known!: {msg}")
                    else:
                        self.logger.warning(f"=> unknown!")
            
            if not self.stop:       
                self.logger.info("File Backup ended successfull")
                self.update_text(f"File Backup ended successfull", "success", update=True)
        
        except Exception as e:
            self.global_error = True
            self.logger.error(f"Backuping: {e}")
            self.update_text("An error occured on the 'file_backup'-Task. See 'Task-Log.log' for detailed information.", "error")

    def start(self):
        """Starts the task execution in a separate thread to keep the GUI responsive."""
        executor_thread = threading.Thread(target=self.execute)
        executor_thread.start()

    def stop_tasks(self):
        """Stops all running tasks."""
        self.logger.info("Stopping all tasks...")
        self.update_text("Stopping, please wait...", "warning")
        self.subprocesshandler.stop_all_processes()
        self.stop = True