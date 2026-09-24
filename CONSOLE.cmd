@echo off
REM DF_Unified\CONSOLE.cmd -- df_unified console (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" console %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "console"=="console" pause
endlocal & exit /b %RC%
