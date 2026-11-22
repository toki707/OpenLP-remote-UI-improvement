@echo off
REM ==========================================================================
REM OpenLP - Mobile Remote & PC Simplified Mode Installer
REM Licensed under the GNU General Public License v3.0 or later (GPL-3.0-or-later)
REM ==========================================================================

echo Installation de la nouvelle interface Mobile Remote et du Mode Simplifie PC pour OpenLP...

set "OPENLP_DATA=%APPDATA%\openlp\data"
set "REMOTES_DIR=%OPENLP_DATA%\remotes"
set "CONTRIB_DIR=%OPENLP_DATA%\contrib\plugins\remote_enhancements"

if not exist "%REMOTES_DIR%\assets" mkdir "%REMOTES_DIR%\assets"
if not exist "%CONTRIB_DIR%" mkdir "%CONTRIB_DIR%"

copy /Y "%~dp0openlp\core\api\remote_client\index.html" "%REMOTES_DIR%\index.html" >nul
copy /Y "%~dp0openlp\core\api\remote_client\assets\version.js" "%REMOTES_DIR%\assets\version.js" >nul
copy /Y "%~dp0scripts\remoteenhancementsplugin.py" "%CONTRIB_DIR%\remoteenhancementsplugin.py" >nul

echo.
echo Installation terminee avec succes !
echo Redemarrez OpenLP pour activer la barre Mode Simplifie PC et les nouvelles fonctions Mobile Remote.
pause
