@echo off
REM DF_Unified\STATUS.cmd -- df_unified status (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" status %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "status"=="console" pause
endlocal & exit /b %RC%
