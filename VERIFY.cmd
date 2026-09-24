@echo off
REM DF_Unified\VERIFY.cmd -- df_unified verify (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" verify %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "verify"=="console" pause
endlocal & exit /b %RC%
