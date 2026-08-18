@echo off
REM Exe uretimi — gelistirme icin run.bat kullanmaya devam edin.
REM Cikti: dist\teklif-hazirlamaV1.exe
cd /d "%~dp0"

python -m pip install -q "pyinstaller>=6.0"
if errorlevel 1 (
    echo PyInstaller kurulamadi.
    pause
    exit /b 1
)

REM Sadece GUI icin gereken Qt paketleri (tum PySide6 toplanmaz → daha kucuk exe)
python -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name teklif-hazirlamaV1 ^
  --paths src ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --icon "assets\branding\antsis_logo.ico" ^
  --hidden-import teklif_hazirlama ^
  --hidden-import teklif_hazirlama.main ^
  "src\teklif_hazirlama\main.py"

if errorlevel 1 (
    echo Exe uretilemedi.
    pause
    exit /b 1
)

echo.
echo Hazir: %~dp0dist\teklif-hazirlamaV1.exe
echo Bu dosyayi arkadasina atabilirsin. run.bat ve kaynak kod ayni kaldi.
echo.
pause
