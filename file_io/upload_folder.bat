@echo off
setlocal

set "BATCH_ROOT=F:\downloads\batch20"
set "EMAIL_RECIPIENTS=jimtsarouhas@gmail.com,chandrinos@gmail.com"

powershell -ExecutionPolicy Bypass -File "%~dp0process_batch.ps1" -BatchRoot "%BATCH_ROOT%" -Recipients "%EMAIL_RECIPIENTS%"

pause
