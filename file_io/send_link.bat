@echo off
setlocal

if "%~1"=="" (
    echo Usage: send_link.bat ^<url^> [zipname]
    echo Example: send_link.bat https://storage.to/upmj0AnMf myfile.zip
    exit /b 1
)

set "LINK=%~1"
set "ZIPNAME=%~2"
if "%ZIPNAME%"=="" set "ZIPNAME=download.zip"
set "EMAIL_RECIPIENTS=jimtsarouhas@gmail.com,chandrinos@gmail.com"

powershell -ExecutionPolicy Bypass -File "%~dp0send_link_email.ps1" -Link "%LINK%" -ZipName "%ZIPNAME%" -Recipients "%EMAIL_RECIPIENTS%"
