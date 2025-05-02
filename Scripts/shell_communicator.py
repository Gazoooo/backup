import re
import signal
import subprocess
import logging
import os

class ShellCommunicator:
    """
    Handles shell-based file operations like copy and delete for Linux and Windows systems.
    """

    def __init__(self, os_type):
        """
        Initialize the shell communicator for the specified operating system.

        Args:
            os_type (str): The operating system type ('linux' or 'windows').
        """
        self.logger = logging.getLogger(__name__)
        self.running_procs = []
        self.os_type = os_type
        threads = os.cpu_count()
        self.threads_to_use = 16
        self.logger.info(f"Using {self.threads_to_use} threads for robocopy. Total amount of threads in system: {threads}.")
        self.exitcodes_robocopy = {
            0: "No errors occurred, and no files were copied.",
            1: "All files were copied successfully.",
            2: "Some files were copied successfully, but some files were skipped.",
            3: "Some files were copied successfully, and some files were skipped, but no errors occurred.",
            5: "Some files could not be copied due to permission issues.",
            6: "Additional files or directories were detected and not copied.",
            7: "Files were copied successfully, but some files could not be accessed.",
            8: "Some files were copied successfully, and some files could not be accessed.",
            16: "No files copied. This is likely the case because src and dst are identical.",
            3221225786: "Received CTRL+C – robocopy was terminated manually or by system signal."
            
        }
        self.exitcodes_rsync = {
            0: "No errors occurred.",
            1: "Some files were copied successfully, but some files were skipped.",
            2: "Some files were copied successfully, and some files were skipped, but no errors occurred.",
            3: "Some files could not be copied due to permission issues.",
            4: "Additional files or directories were detected and not copied.",
            5: "Files were copied successfully, but some files could not be accessed.",
            19: "Received SIGUSR1 – process was interrupted, likely due to a related process exiting.",
            20: "Received SIGINT/SIGTERM/SIGHUP – rsync was terminated manually or by system signal."
        }

    def get_exitcode(self, mode, exitcode):
        """
        Returns a human-readable message based on the exit code of the last command.

        Args:
            exitcode (int): The exit code from the last command.
            mode (str): The mode of operation ('clean' or 'backup').

        Returns:
            str: A message describing the exit code when it is in dicrtionary.
            None: If the exit code is not found in the dictionary.
            """
        match mode:
            case "clean":
                return NotImplementedError("get_exitcode(): Clean mode not implemented.")
            case "backup":
                if self.os_type == "linux":
                    return self.exitcodes_rsync.get(exitcode, None)
                elif self.os_type == "windows":
                    return self.exitcodes_robocopy.get(exitcode, None)
            case _:
                raise ValueError(f"get_exitcode(): Unknown mode '{mode}'.")
        
    def delete(self, dir, is_file=False):
        """
        Deletes a file or directory based on the OS type.

        Args:
            dir (str): Path to the file or directory.
            is_file (bool): If True, delete as file; otherwise as directory.
        """
        self.logger.debug(f"Now deleting '{dir}' ...")
        try:
            match self.os_type:
                case "linux":
                    result = self._delete_linux(dir)
                case "windows":
                    result = self._delete_windows(dir, is_file)
            self.logger.debug(f"Deleted success.")
        except Exception as e:
            self.logger.error(f"delete(): {e}.")
            raise e

    def _delete_windows(self, dir, is_file):
        """
        Deletes a file or folder using Windows shell commands.

        Args:
            dir (str): Path to file or folder.
            is_file (bool): Whether the path is a file.
        """
        if not is_file:
            cmd = ["RD", "/S", "/Q", dir]
        else:
            cmd = ["del", "/F", dir]
        result = subprocess.run(cmd, check=True, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return result

    def _delete_linux(self, dir):
        """
        Deletes a file or folder using Linux shell command.

        Args:
            dir (str): Path to file or folder.
        """
        cmd = ["rm", "-rf", dir]
        result = subprocess.run(cmd, check=True, shell=False)
        return result

    def copy(self, src, dst):
        """
        Copies a file or directory from src to dst using OS-specific tools.

        Args:
            src (str): Source path.
            dst (str): Destination path.

        Returns:
            subprocess.Popen: The process object handling the copy.
        """
        self.logger.debug(f"Now backupping '{src}' to '{dst}' ...")
        try:
            match self.os_type:
                case "linux":
                    process = self._copy_linux(src, dst)
                case "windows":
                    process = self._copy_windows(src, dst)
            self.running_procs.append(process)
            return process
        except Exception as e:
            self.logger.error(f"copy(): Error ({e}).")
            raise e

    def _copy_linux(self, src, dst):
        """
        Performs a copy using rsync on Linux.

        Args:
            src (str): Source path.
            dst (str): Destination path.

        Returns:
            subprocess.Popen: The running rsync process.
        """
        if os.path.isdir(src):
            pass
        cmd = ["rsync", "--mkpath", "-az", "--info=progress2", "--no-perms", "--delete", "--inplace", "--copy-unsafe-links", src, dst]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
        return process

    def _copy_windows(self, src, dst):
        """
        Performs a copy using robocopy on Windows.

        Args:
            src (str): Source path.
            dst (str): Destination path.

        Returns:
            subprocess.Popen: The running robocopy process.
        """
        if os.path.isdir(src):
            dst = os.path.join(dst, os.path.basename(src))
        cmd = ["robocopy", src, dst, "/R:3", "/W:5", "/B", "/E", "/Z", f"/MT:{self.threads_to_use}", "/MIR"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return process

    def parse_progress(self, line, copied_files, total_files):
        """
        Parses a line of copy output to extract progress percentage.

        Args:
            line (str): Output line from the subprocess.
            copied_files (int): Number of files already copied.
            total_files (int): Total number of files.

        Returns:
            float or None: Estimated total progress in percent, or None if not parsable.
        """
        match self.os_type:
            case "linux":
                percent = self._parse_progress_rsync(line)
            case "windows":
                percent = self._parse_progress_robocopy(line, copied_files, total_files)
        return percent

    def _parse_progress_rsync(self, line):
        """
        Parses rsync progress output.

        Args:
            line (str): Output line from rsync.

        Returns:
            int or None: Percent of completion, or None if not found.
        """
        match = re.search(r'(\d+)%', line)
        if match:
            percent = int(match.group(1))
            return percent

    def _parse_progress_robocopy(self, line, copied_files, total_files):
        """
        Parses robocopy progress output.

        Args:
            line (str): Output line from robocopy.
            copied_files (int): Number of copied files so far.
            total_files (int): Total number of files to be copied.

        Returns:
            float or None: Estimated total progress in percent, or None if not found.
        """
        match = re.search(r'(\d+)%', line)
        if match:
            file_percent = int(match.group(1))
            total_percent = (file_percent / 100 / total_files + (copied_files - 1) / total_files) * 100
            return total_percent

    def stop_all_processes(self):
        """
        Stops all running processes.
        """
        self.logger.debug("Stopping all processes...")
        try:
            for proc in self.running_procs:
                if proc:
                    if proc.poll() is None: #does process live?
                        if self.os_type == "linux":
                            os.killpg(os.getpgid(proc.pid), signal.SIGINT)  # Unix-style Ctrl+C to process group
                        elif self.os_type == "windows":
                            proc.send_signal(signal.CTRL_BREAK_EVENT)  # Windows-style Ctrl+Break to process group
                        proc.wait()  # Wait for the subprocess to finish
                        self.logger.debug(f"Stopped process {proc.pid}")
        except Exception as e:
            self.logger.error(f"stop_all_processes(): {e}.")
            raise e