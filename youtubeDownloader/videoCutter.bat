@echo off
setlocal enabledelayedexpansion
for %%a in (*.mp4) do (
    set "filename=%%~na"
    set "foldername=!filename: =_!"
    mkdir "!foldername!"
    ffmpeg -i "%%a" -vf "yadif,pp7,unsharp,fps=1" -q:v 1 "!foldername!/%%05d.jpg"
)
pause


 