import re
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
        self.os_type = os_type
        threads = os.cpu_count()
        self.threads_to_use = 16
        self.logger.info(f"Using {self.threads_to_use} threads for robocopy. Total amount of threads in system: {threads}.")

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
        result = subprocess.run(cmd, check=True, shell=True)
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
        cmd = ["rsync", "--mkpath", "-avz", "--info=progress2", src, dst]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
        cmd = ["robocopy", src, dst, "/E", "/Z", f"/MT:{self.threads_to_use}"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
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
