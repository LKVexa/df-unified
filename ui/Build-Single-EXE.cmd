@echo off
setlocal EnableExtensions DisableDelayedExpansion
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Build-Single-EXE.ps1"
set "RC=%errorlevel%"
if not "%RC%"=="0" pause
exit /b %RC%
