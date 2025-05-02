import time
import logging
import os as os
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import messagebox
from tools import window_in_middle, change_text
import atexit

from executor import Executor
from shell_communicator import ShellCommunicator
from file_handler import FileHandler
from device_communicator import DeviceCommunicator



class View:
    """
    Main class to handle the GUI for the PC Utils application. It includes setup for tasks, folder management,
    and user settings. It also provides interaction with system-level operations such as backups and virus scans.
    """
    def __init__(self, testing=False, fast=False): 
        """
        Initializes the View class by setting up logging, user settings, and creating the graphical user interface (GUI).
        
        Args:
            testing (bool): If True, sets the hostname to a test one for testing purposes.
            fast (bool): If True, enables fast mode for quicker operations.
        """
        #create log
        dc = DeviceCommunicator()
        if not testing:
            self.hostname = dc.get_hostname()
        else:
            self.hostname = "test_win" if dc.get_os() == "windows" else "test_lin"
        self.osType = dc.get_os()
        self.userPath = dc.get_path("~")
        self.rootPath = dc.get_path("/")
        self.filehandler = FileHandler(self.hostname, self.userPath)
        try:
            self.filehandler.setup_logger()
        except Exception as e:
            change_text(self.log, f"Couldn't create the log for this session. ({e})\nExiting program in 3s...", "error")
            self.log.update_idletasks()
            time.sleep(3)
            exit()
        self.logger = logging.getLogger(__name__)
        
        #does user exists?
        self.filehandler.parse_yaml()
        self.user_found = self.filehandler.search_user()
        if not self.user_found:
            messagebox.showwarning("Warning", f"Unknown Host '{self.hostname}'.\nA standard profile for you is created.\nOtherwise you can change your hostname in your OS settings.")
            self.filehandler.add_Host()
            
        #create gui
        self.backupfenster = tk.Tk()
        self.create_style()
        self.backupfenster.configure(bg=self.color_palette[0])
        self.backupfenster.title("PC Utils")
        window_in_middle(self.backupfenster,1500,800)
        self.create_guiElements()
        self.filehandler.set_callback(self.update_log)
        atexit.register(self.cleanup)
        self.destDir_folders_list.bind("<<ComboboxSelected>>", self.edit_destDir)
        
        #set user settings from yaml
        self.info_dict, self.backupPaths_list, self.destPaths_list = self.filehandler.get_userContent()
        self.data_init()
        self.taskRunning = False
        
    def create_style(self):
        """
        Creates custom styles for the tkinter widgets, such as colors and font styling.
        """
        #colors (#dark to light in lists)
        self.color_palette = ["#4D2D18", "#8A6240", "#CABA9C"] 
        self.lightred = "#FF474C"
        self.lightgreen = "#41DC8E"
        
        self.style = ttk.Style()
        self.style.configure("Custom.TLabel", font=("Arial", 16), background=self.color_palette[2], foreground="white")
        self.style.configure("Custom.TCheckbutton", font=("Arial", 16), background=self.color_palette[1], foreground="white", width=25) 
        
    def create_guiElements(self):
        """
        Creates the GUI elements (frames, buttons, labels, checkboxes) and sets their behavior.
        """
        #self.last_made_clear_temp = self.last_made_check_smartphoneBackup = self.last_made_check_virusScan = self.last_made_check_healthScan = self.last_made_check_fileBackup = tk.StringVar
        #print(self.last_made_clear_temp)
        #print(self.last_made_check_healthScan)
        
        self.mainframe_choosing_task = tk.Frame(self.backupfenster, bg=self.color_palette[1], height=750, width=350)
        self.mainframe_choosing_task.place(x=10,y=10)
        self.mainframe_choosing_folders = tk.Frame(self.backupfenster, bg=self.color_palette[1], height=750, width=400)
        self.mainframe_choosing_folders.place(x=400, y=10)

        self.taskChoose = ttk.Label(self.mainframe_choosing_task, text=f"Choose tasks to complete.", 
                                    style="Custom.TLabel", background=self.color_palette[2])
        self.taskChoose.place(x=10,y=10)

        self.check_clean = ttk.Checkbutton(self.mainframe_choosing_task, text=f"Clean (Remove old backups)", style="Custom.TCheckbutton")
        self.check_clean.state(['!alternate', 'selected'])
        self.check_clean.place(x=10, y=100)
        self.check_smartphoneBackup = ttk.Checkbutton(self.mainframe_choosing_task, text="Smartphone Backup", style="Custom.TCheckbutton")
        self.check_smartphoneBackup.state(['!alternate', 'disabled'])
        self.check_smartphoneBackup.place(x=10, y=200)
        self.check_virusScan = ttk.Checkbutton(self.mainframe_choosing_task, text="Virenscan", style="Custom.TCheckbutton")
        self.check_virusScan.state(['!alternate','disabled'])
        self.check_virusScan.place(x=10,y=300)
        self.check_healthScan = ttk.Checkbutton(self.mainframe_choosing_task, text="Health Scan", style="Custom.TCheckbutton")
        self.check_healthScan.state(['!alternate', 'disabled'])
        self.check_healthScan.place(x=10, y=400)
        self.check_fileBackup = ttk.Checkbutton(self.mainframe_choosing_task, text="File Backup",style="Custom.TCheckbutton")
        self.check_fileBackup.state(['!alternate', 'selected'])
        self.check_fileBackup.place(x=10, y=500)
        
        self.confirm = tk.Button(self.mainframe_choosing_task, text ="Execute tasks",bg="green", command=self.go)
        self.confirm.place(x=10,y=650)
        self.stop = tk.Button(self.mainframe_choosing_task, text="Stop tasks", bg="red", command=self.stop_tasks)
        self.stop.place(x=150,y=650)
        self.stop.config(state="disabled")
        
        self.backup_folders_list = tk.Listbox(self.mainframe_choosing_folders, width=47, height=10)
        self.backup_folders_list.place(x=10,y=50)
        self.clean_folders_list = tk.Listbox(self.mainframe_choosing_folders, width=47, height=10)
        self.clean_folders_list.place(x=10,y=440)
        self.destDir_folders_list = ttk.Combobox(self.backupfenster, height=10, state="readonly")
        self.destDir_folders_list.place(x=1100,y=750)

        self.add_folders_backup_button = tk.Button(self.mainframe_choosing_folders, bg=self.lightgreen, text="Add Folders to backup", 
                                                   command=lambda: self.edit_folder("add", self.backup_folders_list, "paths.backup_paths"))
        self.add_folders_backup_button.place(x=10,y=10)
        self.remove_folders_backup_button = tk.Button(self.mainframe_choosing_folders, bg=self.lightred, text="Remove selected", 
                                                      command=lambda: self.edit_folder("remove", self.backup_folders_list, "paths.backup_paths"))
        self.remove_folders_backup_button.place(x=200,y=10)
        self.add_folders_clean_button = tk.Button(self.mainframe_choosing_folders, text="Add Folders to clean (Not implemented)", bg=self.lightgreen,
                                                  command=lambda: self.edit_folder("add", self.clean_folders_list, "paths.clean_paths"))
        self.add_folders_clean_button.place(x=10,y=400)
        self.add_folders_clean_button.config(state='disabled')

        
        self.add_destDir_button = tk.Button(self.backupfenster, bg=self.lightgreen, text="Add destDir", 
                                            command=lambda: self.edit_destDir(mode="add"))
        self.add_destDir_button.place(x=850,y=700)
        self.remove_destDir_button = tk.Button(self.backupfenster, bg=self.lightred, text="Remove selected destDir", 
                                               command=lambda: self.edit_destDir(mode="remove"))
        self.remove_destDir_button.place(x=850,y=750)

        self.log = tk.Text(self.backupfenster, state="disabled", width=75, height=30)
        self.log.place(x=850,y=10)
        self.log.tag_configure("error", foreground="red")
        self.log.tag_configure("warning", foreground="orange")
        self.log.tag_configure("success", foreground="green")
        
        self.label_info = ttk.Label(self.backupfenster, text="", font=("Arial", 14), width=60, wraplength=600, style="Custom.TLabel")
        self.label_info.place(x=850,y=550)
            
    def go(self):
        """
        Prepares the selected tasks by collecting information about the folders to back up, clean, or scan, 
        then passes the tasks to an executor for execution.
        """
        self.confirm.config(state="disabled")
        self.stop.config(state="normal")
        change_text(self.log, "", clear=True)
        
        try:
            self.filehandler.write_yaml()
            self.info_dict, self.backupPaths_list, self.destPaths_list = self.filehandler.get_userContent()
            backupDst = self.filehandler.create_backupPath() #not optimal here, but method has to be called before filehandler.check_old_backups()
            task_infos = {}
            if self.check_clean.instate(['selected']):
                task_infos["clean"] = {"cleanPaths": [],
                                       "oldBackups": self.filehandler.check_old_backups("backups")
                                       }   
            if self.check_smartphoneBackup.instate(['selected']):
                task_infos["smartphone_backup"] = {"None": "None"}
            if self.check_virusScan.instate(['selected']):
                task_infos["virus_scan"] = {"None": "None"}
            if self.check_healthScan.instate(['selected']):
                task_infos["health_scan"] = {"None": "None"}
            if self.check_fileBackup.instate(['selected']):
                task_infos["file_backup"] = {
                    "dstPath": backupDst,
                    "backupPaths": self.backupPaths_list
                }
        except Exception as e:
            self.logger.error(f"go: {e}")
            change_text(self.log, "Error at preparing. See 'Task-Log.log' for more information. Exit program in 3s...", "error")
            self.log.update_idletasks()
            time.sleep(3)
            exit()
        change_text(self.log, "Successfully prepared everything.", "success")

        #start executor to execute tasks
        self.taskRunning = True
        self.sc = ShellCommunicator(self.osType)
        self.ex = Executor(self.sc, self.update_log, self.update_rdy)
        self.ex.set_details(task_infos)
        self.ex.start()

    def edit_destDir(self, event=None, mode=None):
        """
        Allows the user to select or remove a destination directory for backup. Updates the GUI and YAML file accordingly.
        """
        self.confirm.config(state="normal")
        match mode:
            case "add":
                folder = tk.filedialog.askdirectory(title="Select Destination", parent=self.backupfenster, initialdir=self.userPath)
                if folder:
                    self.filehandler.update_yaml("paths.dest_paths", folder)
                    #append to combobox
                    current_values = list(self.destDir_folders_list['values'])
                    if folder not in current_values:
                        current_values.append(folder)
                    self.destDir_folders_list['values'] = current_values
                    self.destDir_folders_list.set(folder)
                    
            case "remove":
                curDir = self.destDir_var.get()
                values = list(self.destDir_folders_list['values'])
                if curDir in values and len(values) > 1:
                    values.remove(curDir)
                    self.destDir_folders_list['values'] = values
                    self.destDir_folders_list.set(values[0])
                    self.filehandler.update_yaml("paths.dest_paths", curDir, delete=True)
                    
        selected = self.destDir_folders_list.get() 
        if selected != "Choose your DestDir...": #something is selected
            if not os.path.exists(selected):
                change_text(self.log, f"The selected path '{selected}' doesn't exists, ignored it!", "warning")
                self.confirm.config(state="disabled")
            else:
                self.destDir_var.set(selected)
                self.update_infoString(selected)
                self.filehandler.update_yaml("info.last_selected_dest", selected)
                self.filehandler.backup_alreadyExists()
            
        self.destDir_folders_list.set("Choose your DestDir...")
        self.destDir_folders_list.selection_clear()
        self.backupfenster.focus_set()
      
    def edit_folder(self, mode, refList, yaml_key):
        """
        Allows the user to add or remove folders from the backup or clean lists, updating the respective GUI list and YAML file.
        
        Args:
            mode (str): The mode of operation, either "add" or "remove".
            refList (tk.Listbox): The listbox reference to update.
            yaml_key (str): The key in the YAML file to update.
        """
        match mode:
            case "add":
                folder = tk.filedialog.askdirectory(title="Select Folder", parent=self.backupfenster, initialdir=self.userPath)
                existing_folders = refList.get(0, tk.END) 
                print(existing_folders)
                if self.filehandler.visualize_path(folder, short=True) not in existing_folders:
                    self.filehandler.update_yaml(yaml_key, folder)
                    refList.insert(tk.END, self.filehandler.visualize_path(folder, short=True))
                    if "backup" in yaml_key:
                        self.BackupSize_var.set(self.BackupSize_var.get() + self.filehandler.get_size(folder))
                    
            case "remove":
                selection = refList.curselection()
                if selection:
                    index = selection[0]
                    path = refList.get(index)
                    refList.delete(index)
                    self.filehandler.update_yaml(yaml_key, path, delete=True)
                    if "backup" in yaml_key:
                        self.BackupSize_var.set(self.BackupSize_var.get() - self.filehandler.get_size(path))
                        
        self.update_infoString(self.destDir_var.get())

    def update_infoString(self, selectedDestPath):
        """
        Updates the information string displayed in the GUI based on the selected destination directory.
        
        Args:
            selectedDestPath (str): The path of the selected destination directory.
        """
        details_string = f"Device-Name: {self.hostname}\n"
        details_string += f"Selected destination: {self.filehandler.visualize_path(selectedDestPath)}\n"
        details_string += f"Backup size: {self.BackupSize_var.get():.2f} GB\n"
        self.label_info.config(text=details_string)
        
    def data_init(self):
        """
        Initial method.
        1. check if backup from today already exists
        2. initialize TK vars
        3. fill the combobox with destdir list
        4. fill in specific paths for backup/clean
        """
        if self.filehandler.backup_alreadyExists():
            self.update_log(f"Backup from today already exists.", "warning")
            self.update_log("=> For a backup the destination will be mirrored 1:1 with the source (including deletion of missing files).", "warning")
            self.logger.warning(f"Backup from today already exists. Mirroring active!!!")
            
        self.last_destPath_selected = self.info_dict["last_selected_dest"]
        self.destDir_var = tk.StringVar(value=self.last_destPath_selected)
        self.BackupSize_var = tk.DoubleVar(value=0)
        
        self.destDir_folders_list['values'] = self.destPaths_list
        self.destDir_folders_list.set(self.last_destPath_selected)  
        self.edit_destDir()
        
        for path in self.backupPaths_list:
            self.backup_folders_list.insert(tk.END, self.filehandler.visualize_path(path, short=True))
            self.BackupSize_var.set(self.BackupSize_var.get() + self.filehandler.get_size(path))
        clean_list = [] #TODO
        for path in clean_list:
            self.clean_folders_list.insert(tk.END, self.filehandler.visualize_path(path, short=True))
            
        self.update_infoString(self.last_destPath_selected)
            
    def update_log(self, text, tag=None, clear=False, update=False):
        """
        #callback function for executor to be able to update gui log
        Updates the confirmation button state to either 'normal' or 'disabled' based on the execution process.
        """
        change_text(self.log, text, tag=tag, clear=clear, update=update)
    
    def update_rdy(self):
        """callback function for executor to be able to communicate that it is rdy
        """
        self.taskRunning = False
        self.confirm.config(state="normal")
        self.stop.config(state="disabled")
        
    def cleanup(self):
        """performs a cleanup with atexit()
        """
        self.logger.debug("Cleaning up...")
        for h in self.logger.handlers:
            h.flush()
            h.close()
        self.filehandler.write_yaml()  
        if self.taskRunning:
            self.stop_tasks() 
        self.backupfenster.quit()
        
    def stop_tasks(self):
        """Stops all tasks.
        """
        if hasattr(self, 'ex'):
            self.ex.stop_tasks()
        
    def start(self):
        self.backupfenster.mainloop()