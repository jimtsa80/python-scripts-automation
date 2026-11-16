@echo off
setlocal
cd /d "%~dp0.."
REM Local weights only. Pass another .pt as the first argument to override.
set "SYNC=C:\Users\jimts\Documents\projects\live_sync"
set "WORK=C:\Users\jimts\Documents\projects\live_work"
set "WEIGHTS=%~1"
if "%WEIGHTS%"=="" set "WEIGHTS=C:\Users\jimts\Documents\projects\yolov8s.pt"
python anno_live\live_trainer.py --sync-folder "%SYNC%" --frames-root "D:\downloads" --work-dir "%WORK%" --base-weights "%WEIGHTS%" --device 0 --batch 4 --workers 2 --predict-batch 4 --gpu-mem-fraction 0.7 --min-free-vram-mb 1536
if errorlevel 1 pause
endlocal
