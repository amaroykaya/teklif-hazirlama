@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [HATA] Python bulunamadi.
    echo.
    echo Bu program kaynak kod olarak calisir; once Python 3.11+ kurulmali.
    echo Kurulum: https://www.python.org/downloads/
    echo Kurarken "Add python.exe to PATH" kutusunu isaretleyin.
    echo.
    echo Sonra bu klasorde komut isteminde:
    echo   pip install -e .
    echo.
    pause
    exit /b 1
)

python -m teklif_hazirlama.main
if errorlevel 1 (
    echo.
    echo [HATA] Program baslamadi. Yukaridaki mesaji okuyun.
    echo Paketler kurulu degilse: pip install -e .
    echo.
    pause
    exit /b 1
)
