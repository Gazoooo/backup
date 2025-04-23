#wraps methods to low-level shell calls
#for this, uses subprocess

import re
import subprocess
import logging
import os

class ShellCommunicator:
    def __init__(self, os_type):
        self.logger = logging.getLogger(__name__)
        self.os_type = os_type
        threads = os.cpu_count()
        self.threads_to_use = 16
        self.logger.info(f"Using {self.threads_to_use} threads for robocopy. Total amount of threads in system: {threads}.")

        
    
    def delete(self, dir, is_file=False):
        self.logger.debug(f"Now deleting '{dir}' ...")
        try:
            match self.os_type:
                case "linux":
                    result = self._delete_linux(dir)
                case "windows":
                    result = self._delete_windows(dir, is_file)
                    
            self.logger.debug(f"Deleted success.")
            #return result
        except Exception as e:
            self.logger.error(f"delete(): {e}.")
            raise e
                
    def _delete_windows(self, dir, is_file):
        if not is_file:
            cmd = ["RD", "/S", "/Q", dir]
            result = subprocess.run(cmd, check=True, shell=True)
        else:
            cmd = ["del", "/F", dir]
            result = subprocess.run(cmd, check=True, shell=True) #experimental
        return result
    
    def _delete_linux(self, dir):
        cmd = ["rm", "-rf", dir]
        result = subprocess.run(cmd, check=True, shell=False) #experimental
        return result


    def copy(self, src, dst):
        self.logger.debug(f"Now backupping '{src}' to '{dst}' ...")
        try:
            match self.os_type:
                case "linux":
                    process = self._copy_linux(src, dst)
                case "windows":
                    process = self._copy_windows(src, dst)
            return process
        except Exception as e:
            self.logger.error(f"copy(): Error ({e}).")
            raise e
        
    def _copy_linux(self, src, dst):
        if os.path.isdir(src):
            pass
        cmd = ["rsync", "--mkpath", "-avz", "--info=progress2", src, dst]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process

    def _copy_windows(self, src, dst):
        if os.path.isdir(src):
            dst = os.path.join(dst, os.path.basename(src))
        cmd = ["robocopy", src, dst, "/E", "/Z", f"/MT:{self.threads_to_use}"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        return process
        
    
    def parse_progress(self, line, copied_files, total_files):
        match self.os_type:
            case "linux":
                percent = self._parse_progress_rsync(line)
            case "windows":
                percent = self._parse_progress_robocopy(line, copied_files, total_files)
        return percent

    def _parse_progress_rsync(self, line):
        match = re.search(r'(\d+)%', line)
        if match:
            percent = int(match.group(1))
            return percent
        
    def _parse_progress_robocopy(self, line, copied_files, total_files):
        match = re.search(r'(\d+)%', line)
        if match:
            file_percent = int(match.group(1))
            total_percent = (file_percent/100 / total_files + (copied_files-1)/total_files) * 100
            return total_percent       
            