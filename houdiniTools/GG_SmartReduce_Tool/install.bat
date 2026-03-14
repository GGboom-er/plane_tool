@echo off
setlocal

set "PLUGIN_DIR=%~dp0"
if "%PLUGIN_DIR:~-1%"=="\" set "PLUGIN_DIR=%PLUGIN_DIR:~0,-1%"

set "HOUDINI_DOCS=%USERPROFILE%\Documents\houdini21.0"
set "PACKAGES_DIR=%HOUDINI_DOCS%\packages"
set "JSON_FILE=%PACKAGES_DIR%\GG_SmartReduce.json"

if not exist "%HOUDINI_DOCS%" (
    echo ERROR: Houdini 21.0 folder not found in Documents.
    pause
    exit /b 1
)

if not exist "%PACKAGES_DIR%" mkdir "%PACKAGES_DIR%"

echo Installing Plugin...
echo Source: %PLUGIN_DIR%

powershell -NoProfile -Command "$root = '%PLUGIN_DIR%'.Replace('\', '/'); $py = $root + '/python'; $json = '{ \"env\": [ { \"GG_ROOT\": \"' + $root + '\" }, { \"HOUDINI_PATH\": \"$GG_ROOT\" }, { \"PYTHONPATH\": \"' + $py + '\" } ] }'; Set-Content -LiteralPath '%JSON_FILE%' -Value $json -Encoding ASCII"

if %ERRORLEVEL% EQU 0 (
    echo SUCCESS: Configuration written.
    echo Please restart Houdini.
) else (
    echo ERROR: Failed to write JSON.
)

pause