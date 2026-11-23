@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo Active o cree el entorno virtual siguiendo README.md.
  pause
  exit /b 1
)
"venv\Scripts\python.exe" manage.py runserver --settings=sgr.settings_pruebas
