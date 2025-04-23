# Auto-Backup your files!

This is a python program I made where you can choose, which files t obackup where.

Note that this is work in progress!
Note that in the moment only the backup task is implemented.
at the moment only works with folders, not single files!

## Rough structure

1. view is called
2. the `config.yaml`is parsed for
   1. checking if user is known, if not create new
   2. get suer data (files, backup paths, ...) from existing user
3. user can config sth in the gui
4. if task finally is started, the information needed to execute this tasks will be passed in a dict to the `executor.py`
5. whe user closes the gui window, the `config.yaml` is updated
6. if an error occures, you can read about it in the `Task-Log.log` produced (same dir where the main program is)

## Requirements

a full `requirements.txt` will be added later

For now:
- rsync>=3.1.0
- python>=3.10