@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_rigitnow.ps1" %*
set "rigitnow_exit=%ERRORLEVEL%"
if not "%rigitnow_exit%"=="0" echo rigitnow installation failed.
if "%~1"=="" pause
exit /b %rigitnow_exit%
