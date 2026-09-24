@echo off
REM DF_Unified\MEMBERS.cmd -- df_unified members (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" members %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "members"=="console" pause
endlocal & exit /b %RC%
