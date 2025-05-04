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
            change_text(self.log_text, f"Couldn't create the log for this session. ({e})\nExiting program in 3s...", "error")
            self.log_text.update_idletasks()
            time.sleep(3)
            exit()
        self.logger = logging.getLogger(__name__)
        
        #does user exists?
        self.filehandler.parse_yaml()
        if not self.filehandler.search_user():
            messagebox.showwarning("Warning", f"Unknown Host '{self.hostname}'.\nA standard profile for you is created.\nOtherwise you can change your hostname in your OS settings.")
            self.filehandler.add_Host()
            
        #create gui
        self.root = tk.Tk()
        self.create_style()
        self.root.configure(bg=self.color_palette[0])
        self.root.title("PC Utils")
        window_in_middle(self.root,1500,800)
        self.create_guiElements()
        self.filehandler.set_callback(self.update_log)
        atexit.register(self.cleanup)
        self.destDirs_combobox.bind("<<ComboboxSelected>>", self.edit_destDir)
        
        #set user settings from yaml
        self.info_dict, self.backupPaths_list, self.destPaths_list = self.filehandler.get_userContent()
        self.cleanPaths_list = [] #TODO
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
        default_font = ("TkDefaultFont", 14)
        label_font = ("TkHeadingFont", 14)
        text_font = ("TkTextFont", 12)
        self.style.configure("Custom.TLabel", font=label_font, background=self.color_palette[2], foreground="white")
        self.style.configure("Custom.TCheckbutton", font=default_font, background=self.color_palette[1], foreground="white", width=25) 
        
    def create_guiElements(self):
        """
        Creates the GUI elements (frames, buttons, labels, checkboxes) and sets their behavior.
        """
        #self.last_made_clear_temp = self.last_made_check_smartphoneBackup = self.last_made_check_virusScan = self.last_made_check_healthScan = self.last_made_check_fileBackup = tk.StringVar
        #print(self.last_made_clear_temp)
        #print(self.last_made_check_healthScan)
        
        self.mainframe_choosing_task = tk.Frame(self.root, bg=self.color_palette[1], height=750, width=350)
        self.mainframe_choosing_task.place(x=10,y=10)
        self.mainframe_choosing_folders = tk.Frame(self.root, bg=self.color_palette[1], height=750, width=400)
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
        
        self.confirm_button = tk.Button(self.mainframe_choosing_task, text ="Execute tasks",bg="green", command=self.go)
        self.confirm_button.place(x=10,y=650)
        self.stop_button = tk.Button(self.mainframe_choosing_task, text="Stop tasks", bg="red", command=self.stop_tasks)
        self.stop_button.place(x=150,y=650)
        self.stop_button.config(state="disabled")
        
        self.backupDirs_listbox = tk.Listbox(self.mainframe_choosing_folders, width=47, height=10)
        self.backupDirs_listbox.place(x=10,y=50)
        self.cleanDirs_listbox = tk.Listbox(self.mainframe_choosing_folders, width=47, height=10)
        self.cleanDirs_listbox.place(x=10,y=440)
        self.destDirs_combobox = ttk.Combobox(self.root, height=10, state="readonly")
        self.destDirs_combobox.place(x=1100,y=750)

        self.addBackupDir_button = tk.Button(self.mainframe_choosing_folders, bg=self.lightgreen, text="Add Folders to backup", 
                                                   command=lambda: self.edit_folder("add", self.backupDirs_listbox, "paths.backup_paths"))
        self.addBackupDir_button.place(x=10,y=10)
        self.removeBackupDir_button = tk.Button(self.mainframe_choosing_folders, bg=self.lightred, text="Remove selected", 
                                                      command=lambda: self.edit_folder("remove", self.backupDirs_listbox, "paths.backup_paths"))
        self.removeBackupDir_button.place(x=200,y=10)
        self.addCleanDir_button = tk.Button(self.mainframe_choosing_folders, text="Add Folders to clean (Not implemented)", bg=self.lightgreen,
                                                  command=lambda: self.edit_folder("add", self.cleanDirs_listbox, "paths.clean_paths"))
        self.addCleanDir_button.place(x=10,y=400)
        self.addCleanDir_button.config(state='disabled')

        
        self.addDestDir_button = tk.Button(self.root, bg=self.lightgreen, text="Add destDir", 
                                            command=lambda: self.edit_destDir(mode="add"))
        self.addDestDir_button.place(x=850,y=700)
        self.removeDestDir_button = tk.Button(self.root, bg=self.lightred, text="Remove selected destDir", 
                                               command=lambda: self.edit_destDir(mode="remove"))
        self.removeDestDir_button.place(x=850,y=750)

        self.log_text = tk.Text(self.root, state="disabled", width=75, height=30)
        self.log_text.place(x=850,y=10)
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("success", foreground="green")
        
        self.info_label = ttk.Label(self.root, text="", style="Custom.TLabel")
        self.info_label.place(x=850,y=550)
            
    def go(self):
        """
        Prepares the selected tasks by collecting information about the folders to back up, clean, or scan, 
        then passes the tasks to an executor for execution.
        """
        self.confirm_button.config(state="disabled")
        self.stop_button.config(state="normal")
        change_text(self.log_text, "", clear=True)
        
        try:
            self.filehandler.write_yaml()
            self.info_dict, self.backupPaths_list, self.destPaths_list = self.filehandler.get_userContent()
            backupDst = self.filehandler.create_backupPath() #not optimal here, but method has to be called before filehandler.check_old_backups()
            task_infos = {}
            if self.check_clean.instate(['selected']):
                task_infos["clean"] = {"cleanPaths": [],
                                       "oldBackups": self.filehandler.check_old_backups("backup")
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
            change_text(self.log_text, "Error at preparing. See 'Task-Log.log' for more information. Exit program in 3s...", "error")
            self.log_text.update_idletasks()
            time.sleep(3)
            exit()
        change_text(self.log_text, "Successfully prepared everything.", "success")

        #start executor to execute tasks
        self.taskRunning = True
        self.subprocesshandler = ShellCommunicator(self.osType)
        self.executor = Executor(self.subprocesshandler, self.update_log, self.update_rdy)
        self.executor.set_details(task_infos)
        self.executor.start()

    def edit_destDir(self, event=None, mode=None):
        """
        Allows the user to select or remove a destination directory for backup. Updates the GUI and YAML file accordingly.
        """
        self.confirm_button.config(state="normal")
        match mode:
            case "add":
                folder = tk.filedialog.askdirectory(title="Select Destination", parent=self.root, initialdir=self.userPath)
                if folder:
                    self.filehandler.update_yaml("paths.dest_paths", folder)
                    #append to combobox
                    current_values = list(self.destDirs_combobox['values'])
                    if self.filehandler.visualize_path(folder) not in current_values:
                        current_values.append(self.filehandler.visualize_path(folder))
                    self.destDirs_combobox['values'] = current_values
                    self.destDirs_combobox.set(folder)
                    
            case "remove":
                curDir = self.destDir_stringvar.get()
                current_values = list(self.destDirs_combobox['values'])
                if curDir in current_values and len(current_values) > 1:
                    current_values.remove(curDir)
                    self.destDirs_combobox['values'] = current_values
                    self.destDirs_combobox.set(current_values[0])
                    self.filehandler.update_yaml("paths.dest_paths", curDir, delete=True)
                    
        selected = self.destDirs_combobox.get() 
        if selected != "Choose your DestDir...": #something is selected
            if not os.path.exists(selected):
                change_text(self.log_text, f"The selected path '{selected}' doesn't exists, ignored it!", "warning")
                self.confirm_button.config(state="disabled")
            else:
                self.destDir_stringvar.set(selected)
                self.update_infoString(selected)
                self.filehandler.update_yaml("info.last_selected_dest", selected)
                self.filehandler.backup_alreadyExists()
            
        self.destDirs_combobox.set("Choose your DestDir...")
        self.destDirs_combobox.selection_clear()
        self.root.focus_set()
      
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
                folder = tk.filedialog.askdirectory(title="Select Folder", parent=self.root, initialdir=self.userPath)
                if folder:
                    existing_folders = refList.get(0, tk.END) 
                    if self.filehandler.visualize_path(folder, short=True) not in existing_folders:
                        self.filehandler.update_yaml(yaml_key, folder)
                        refList.insert(tk.END, self.filehandler.visualize_path(folder, short=True))
                        if "backup" in yaml_key:
                            self.backupSize_doublevar.set(self.backupSize_doublevar.get() + self.filehandler.get_size(folder))
                    
            case "remove":
                selection = refList.curselection()
                print(selection)
                if selection:
                    index = selection[0]
                    visual_path = refList.get(index)
                    refList.delete(index)
                    path = self.filehandler.get_yamlItem("paths.backup_paths", index) # have to restore the path with "..." to an absolut path
                    #print(visual_path, path)
                    self.filehandler.update_yaml(yaml_key, path, delete=True)
                    if "backup" in yaml_key:
                        self.backupSize_doublevar.set(self.backupSize_doublevar.get() - self.filehandler.get_size(path))
                        
        self.update_infoString(self.destDir_stringvar.get())

    def update_infoString(self, selectedDestPath):
        """
        Updates the information string displayed in the GUI based on the selected destination directory.
        
        Args:
            selectedDestPath (str): The path of the selected destination directory.
        """
        details_string = f"Device-Name: {self.hostname}\n"
        details_string += f"Selected destination: {self.filehandler.visualize_path(selectedDestPath)}\n"
        details_string += f"Backup size: {self.backupSize_doublevar.get():.2f} GB\n"
        self.info_label.config(text=details_string)
        
    def data_init(self):
        """
        Initial method.
        1. check if backup from today already exists
        2. initialize TK vars
        3. set last selected destPath
        4. fill in specific paths for backup/clean/destDir
        5. update infoString
        """
        if self.filehandler.backup_alreadyExists():
            self.update_log(f"Backup from today already exists.", "warning")
            self.update_log("=> For a backup the destination will be mirrored 1:1 with the source (including deletion of missing files).", "warning")
            self.logger.warning(f"Backup from today already exists. Mirroring active!!!")
            
        self.destDir_stringvar = tk.StringVar()
        self.backupSize_doublevar = tk.DoubleVar()
        
        self.destDirs_combobox['values'] = self.destPaths_list
        self.last_destPath_selected = self.info_dict["last_selected_dest"]
        self.destDirs_combobox.set(self.last_destPath_selected)
        self.destDir_stringvar.set(self.last_destPath_selected)
        self.edit_destDir() # call this to check if destPath exists
        
        for path in self.backupPaths_list:
            self.backupDirs_listbox.insert(tk.END, self.filehandler.visualize_path(path, short=True))
            self.backupSize_doublevar.set(self.backupSize_doublevar.get() + self.filehandler.get_size(path))
        clean_list = [] #TODO
        for path in clean_list:
            self.cleanDirs_listbox.insert(tk.END, self.filehandler.visualize_path(path, short=True))
        curValues = []
        for path in self.destPaths_list:
            curValues.append(self.filehandler.visualize_path(path))
        self.destDirs_combobox['values'] = curValues
            
        self.update_infoString(self.last_destPath_selected)
            
    def update_log(self, text, tag=None, clear=False, update=False):
        """
        callback function for executor to be able to update gui log
        Updates the confirmation button state to either 'normal' or 'disabled' based on the execution process.
        """
        change_text(self.log_text, text, tag=tag, clear=clear, update=update)
    
    def update_rdy(self):
        """callback function for executor to be able to communicate that it is rdy
        """
        self.taskRunning = False
        self.confirm_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
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
        self.root.quit()
        
    def stop_tasks(self):
        """Stops all tasks.
        """
        if hasattr(self, 'ex'):
            self.executor.stop_tasks()
        
    def start(self):
        self.root.mainloop()