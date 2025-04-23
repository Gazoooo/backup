import subprocess
import os
import re

source_dir = r"C:\Users\user\Desktop\Sonstiges"
src2 = r"AppData/Roaming/Apple Computer/MobileSync"
destination_dir = r"C:\Users\user\Desktop\robocopy_test\dst\\"

# 1. Alle Dateien zählen
total_files = sum(len(files) for _, _, files in os.walk(source_dir))

print(f"📁 Zu kopierende Dateien: {total_files}\n")

# 2. Robocopy-Befehl
command = [
    "robocopy",
    source_dir,
    destination_dir,
    "/E",
    "/Z",
    "/MT:8"
]

#cmd = ["robocopy", src, dst, "/E", "/Z", "/MT:8"]
#process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')

with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace') as process:
    copied_files = 0
    ratio = 0
    total_percent = 0
    win_drive = re.compile(r'\t[A-Z]:\\.*')


    for line in process.stdout:
        #print(win_drive.search(line))
        #print(line.strip())
        #print(copied_files, total_files)
        if re.search(r'\t[A-Z]:\\.*', line): #begins to copy new file
            new_copied += 1
        if '%' in line: 
            match = re.search(r'(\d+)%', line)
            if match:
                file_percent = int(match.group(1))
                total_percent = (file_percent/100 / total_files + (copied_files-1)/total_files) * 100

    print(f"Copying: {total_percent:.2f}% (File: {copied_files}/{total_files})")
    """
