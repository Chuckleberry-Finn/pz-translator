@echo off
echo Running PyInstaller to build executable...

:: Ensure Python is in PATH (or manually set its full path)
set PYTHON_EXECUTABLE="C:\Program Files\Python312\python.exe"

:: Install dependencies
echo Installing required dependencies...
%PYTHON_EXECUTABLE% -m pip install --upgrade pip
%PYTHON_EXECUTABLE% -m pip install PyQt5 deep_translator

:: Define paths
set SCRIPT_PATH=..\pz-translator\translatorGUI.py
set EXE_NAME=pzTranslate
set OUTPUT_PATH=..

:: Run PyInstaller with correct paths
%PYTHON_EXECUTABLE% -m PyInstaller --onefile --windowed --name %EXE_NAME% ^
    --add-data "..\..\pz-translator\translate.py;pz-translator" ^
    --add-data "..\..\pz-translator\LanguagesInfo_b42.json;pz-translator" ^
    --add-data "..\..\pz-translator\LanguagesInfo_b41.json;pz-translator" ^
    --workpath build ^
    --specpath build ^
    --distpath %OUTPUT_PATH% ^
    %SCRIPT_PATH%

echo Build complete!