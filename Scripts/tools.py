import os
from screeninfo import get_monitors

def get_subdirs(parent_dir):
    """
    Returns a list of immediate subdirectories of the given directory.

    This is useful to avoid deleting the parent directory with commands like 'RD' which only support deleting folders.

    Args:
        parent_dir (str): The path to the directory to scan.

    Returns:
        list[str]: A list of absolute paths to subdirectories within parent_dir.
    """
    all_subs = []
    for sub in os.listdir(parent_dir):
        sub_path = os.path.join(parent_dir, sub)
        if os.path.isdir(sub_path):
            all_subs.append(os.path.join(parent_dir, sub))

    norm(all_subs)  # assuming you have this function elsewhere
    return all_subs


def window_in_middle(fenster, breite, hoehe):
    """
    Places a tkinter window in the center of the primary monitor.

    Args:
        fenster (tk.Tk or tk.Toplevel): The tkinter window instance to move.
        breite (int): Desired width of the window.
        hoehe (int): Desired height of the window.
    """
    monitors = get_monitors()
    monitor = monitors[0]

    Breite_Monitor = monitor.width
    Hoehe_Monitor = monitor.height
    x = (Breite_Monitor - breite) // 2
    y = (Hoehe_Monitor - hoehe) // 2
    fenster.geometry(f"{breite}x{hoehe}+{int(x)}+{int(y)}")


def change_text(feld, text, tag=None, clear=False, update=False):
    """
    Changes the content of a tkinter Text widget with optional formatting.

    Args:
        feld (tk.Text): The text widget to modify.
        text (str): The text to insert.
        tag (str, optional): Optional tag for formatting (e.g., color).
        clear (bool): If True, clears the widget before inserting text.
        update (bool): If True, updates (replaces) the current line instead of appending.
    """
    try:
        feld.config(state="normal")  # make editable
        
        if clear:
            feld.delete('1.0', "end")
            return
        
        if update:
            current_line_start = feld.index("insert linestart - 1 lines")
            current_line_end = feld.index("insert lineend")
            feld.delete(current_line_start, current_line_end)
            
        if tag:
            feld.insert("end", f"{text}\n", tag)
        else:
            feld.insert("end", f"{text}\n")
        
        feld.config(state="disabled")  # make read-only again
    except Exception as e:
        print(f"Error in change_text: {e}")

