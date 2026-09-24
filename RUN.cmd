@echo off
REM DF_Unified\RUN.cmd -- df_unified run (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" run %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "run"=="console" pause
endlocal & exit /b %RC%
