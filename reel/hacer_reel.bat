@echo off
REM ---------------------------------------------------------------------------
REM  Arma el reel con tu voz. Doble clic, o desde la consola:
REM      hacer_reel.bat           modelo de voz grande (mejor calidad, mas lento)
REM      hacer_reel.bat rapido    modelo chico (util para una primera prueba)
REM  La primera corrida baja unos 4 GB de modelos y puede tardar bastante.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set MODELO=Qwen/Qwen3-TTS-12Hz-1.7B-Base
if /I "%~1"=="rapido" set MODELO=Qwen/Qwen3-TTS-12Hz-0.6B-Base

if not exist mi_voz.wav (
  echo.
  echo  No encuentro mi_voz.wav en esta carpeta.
  echo.
  pause & exit /b 1
)

if not exist .venv\Scripts\python.exe (
  echo  Creando el entorno...
  where uv >nul 2>nul
  if not errorlevel 1 (
    uv venv .venv || goto :error
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt || goto :error
  ) else (
    python -m venv .venv || goto :error
    .venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
  )
)

echo.
echo  Modelo de voz: %MODELO%
echo  Esto puede tardar; no cierres la ventana.
echo.
.venv\Scripts\python.exe hacer_reel_visual.py ^
  --voz mi_voz.wav ^
  --autor "Alexander Noblejas" ^
  --fuente "CEPLAN, Informe Anual de Politicas Nacionales 2025" ^
  --musica musica\fondo.wav ^
  --credito-musica "pista original generada con hacer_musica.py" ^
  --tts %MODELO% || goto :error

echo.
echo  Listo. Revisa salidas\reel.mp4
echo.
pause & exit /b 0

:error
echo.
echo  Algo fallo. Copia el mensaje de arriba y pasamelo.
echo.
pause & exit /b 1
