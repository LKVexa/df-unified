@echo off
setlocal EnableExtensions DisableDelayedExpansion
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Launch-DF-VM-Technical-Institute-Embedded.ps1"
exit /b %errorlevel%
