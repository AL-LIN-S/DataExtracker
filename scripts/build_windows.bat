@echo off
setlocal EnableExtensions

REM Build a windowed CurveExtractor.exe (same GUI as: python -m curve_extractor).
REM Output: E:\tool\CurveExtractor-0.2.0\CurveExtractor.exe
REM Tesseract is NOT bundled.

set "REPO=%~dp0.."
for %%I in ("%REPO%") do set "REPO=%%~fI"

if not defined PY set "PY=python.exe"
if not exist "%PY%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python not found. Install Python 3.10+ or set PY to python.exe
    exit /b 1
  )
  for /f "delims=" %%P in ('where python') do (
    set "PY=%%P"
    goto :have_py
  )
)
:have_py

set "VENV=%REPO%\build\win-venv"
set "VPY=%VENV%\Scripts\python.exe"
set "OUT=E:\tool\CurveExtractor-0.2.0"
set "WORKDIR=%REPO%\build\pyinstaller"
set "DISTDIR=%REPO%\dist"

echo Repo:    %REPO%
echo Python:  %PY%
echo Output:  %OUT%

if not exist "%REPO%\build" mkdir "%REPO%\build"

echo Creating venv...
"%PY%" -m venv "%VENV%"
if errorlevel 1 exit /b 1

echo Installing curve-extractor and PyInstaller...
"%VPY%" -m pip install -U pip
if errorlevel 1 exit /b 1
"%VPY%" -m pip install -e "%REPO%"
if errorlevel 1 exit /b 1
"%VPY%" -m pip install "pyinstaller>=6.11"
if errorlevel 1 exit /b 1

echo Running PyInstaller...
if exist "%DISTDIR%\CurveExtractor" rmdir /S /Q "%DISTDIR%\CurveExtractor"
"%VPY%" -m PyInstaller --noconfirm --clean --distpath "%DISTDIR%" --workpath "%WORKDIR%" "%REPO%\CurveExtractor.spec"
if errorlevel 1 exit /b 1

if not exist "%DISTDIR%\CurveExtractor\CurveExtractor.exe" (
  echo ERROR: PyInstaller did not produce CurveExtractor.exe
  exit /b 1
)

echo Copying to %OUT% ...
if exist "%OUT%" rmdir /S /Q "%OUT%"
mkdir "%OUT%"
xcopy /E /I /Y "%DISTDIR%\CurveExtractor\*" "%OUT%\" >nul
copy /Y "%REPO%\scripts\README-Windows.txt" "%OUT%\README-Windows.txt" >nul

if not exist "%OUT%\CurveExtractor.exe" (
  echo ERROR: %OUT%\CurveExtractor.exe is missing
  exit /b 1
)

echo.
echo Built: %OUT%\CurveExtractor.exe
echo Keep the _internal folder next to the exe. Tesseract is not included.
exit /b 0
