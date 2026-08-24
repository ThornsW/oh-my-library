@echo off
REM Windows: bundle Memo into a single .exe in .\dist\Memo.exe
setlocal
cd /d %~dp0\..

REM Build with whatever environment is already active; fall back to the `memo`
REM env the README sets up.
where pyinstaller >nul 2>&1
if errorlevel 1 (
    mamba run -n memo pyinstaller --clean --noconfirm Memo.spec
) else (
    pyinstaller --clean --noconfirm Memo.spec
)
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete:
dir dist\Memo.exe
