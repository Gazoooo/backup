import os
from screeninfo import get_monitors



#helper function to get subdirs so that RD doesnt delete parent
#ignores files since RD cant delete them
def get_subdirs(parent_dir):
    all_subs = []
    for sub in os.listdir(parent_dir):
        sub_path = os.path.join(parent_dir, sub)
        if os.path.isdir(sub_path):
            all_subs.append(os.path.join(parent_dir, sub))

    norm(all_subs)
    return all_subs


#puts a tkinter window in the middle of the monitor
def window_in_middle(fenster, breite, hoehe):
    # get primary monitor
    monitors = get_monitors()
    monitor = monitors[0] 

    Breite_Monitor = monitor.width
    Hoehe_Monitor = monitor.height
    #print(f"{Breite_Monitor}x{Hoehe_Monitor}")
    x = (Breite_Monitor - breite) // 2
    y = (Hoehe_Monitor - hoehe) // 2
    fenster.geometry(f"{breite}x{hoehe}+{int(x)}+{int(y)}")

#tkinter specific convenience method
def change_text(feld, text, tag=None, clear=False, update=False):
    feld.config(state="normal")  # Textfeld bearbeitbar machen
    
    # Löscht den Text, wenn clear=True
    if clear:
        feld.delete('1.0', "end")
    
    #Aktuelle Zeile updaten
    if update:
        current_line_start = feld.index("insert linestart - 1 lines")  # Anfang der aktuellen Zeile
        current_line_end = feld.index("insert lineend")  # Ende der aktuellen Zeile
        #print(current_line_start, current_line_end)
        feld.delete(current_line_start, current_line_end)  # Löscht die aktuelle Zeile
        
    # Text einfügen
    if tag:
        feld.insert("end", f"{text}\n", tag)
    else:
        feld.insert("end", f"{text}\n")
    
    feld.config(state="disabled")  # Textfeld wieder nur lesbar machen