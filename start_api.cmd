@echo off
rem Windows entry point; forwards options such as --reload to the PowerShell launcher.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_api.ps1" %*
exit /b %errorlevel%
