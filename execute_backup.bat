::script to execute backup script (windows)
::used in root for admin privileges
@echo off

cd /d %~dp0

..\..\Compiler\Python\python.exe "Scripts\main.py"