@echo off
REM Windows: bundle Memo into a single .exe in .\dist\Memo.exe
setlocal
cd /d %~dp0\..

mamba run -n memo pyinstaller --clean Memo.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete:
dir dist\Memo.exe
