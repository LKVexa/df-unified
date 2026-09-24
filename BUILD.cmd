@echo off
REM DF_Unified\BUILD.cmd -- df_unified build (offline; NETWORK=deny)
setlocal
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%~dp0df_unified\cli.py" build %*
set RC=%ERRORLEVEL%
if /I "%~1"=="" if /I not "build"=="console" pause
endlocal & exit /b %RC%
