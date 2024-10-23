@echo off
setlocal enabledelayedexpansion

REM Check if a folder path is provided
if "%~1"=="" (
    echo No folder path provided.
    exit /b 1
)

REM Set the folder path
set "FOLDER=%~1"

REM Check if the folder exists
if not exist "%FOLDER%" (
    echo The folder does not exist.
    exit /b 1
)

REM Iterate over all .xlsx files in the folder
for %%f in ("%FOLDER%\*.xlsx") do (
    echo Processing file: %%f

    REM Run Script 0: Check if Batters has less lines than Homeplate
    echo Running Script 0...
    for /f "delims=" %%i in ('python lines_checker.py "%%f"') do set OUTPUT=%%i
    if "%OUTPUT%"=="false" (
        echo Homeplate is incomplete for file %%f!
        exit /b 1
    ) else (
        echo Batters/Homeplate are ok for file %%f. Check is done!
    )

    echo Continue the procedure for file %%f

    REM Run Script 1: Copy Batters to Homeplate tab
    echo Running Script 1...
    python batters_mover.py "%%f"
    echo Batters are inside Homeplate

    REM Run Script 2: Creates the Inning column
    echo Running Script 2...
    python inning_creator.py "%%f"
    echo Innings are now ready

    REM Run Script 3: Makes duration 1 in each line
    echo Running Script 3...
    python reshaper.py "%%f"

    REM Run Script 4: Concatenates Batters and Reshaped tab together
    echo Running Script 4...
    python concatanator.py "%%f"

    REM Run Script 5: Fills the gaps among players
    echo Running Script 5...
    python gap_filler.py "%%f"

    REM Run Script 6: Fills the gaps in the very beginning if necessary
    echo Running Script 6...
    python gap_start_filler.py "%%f"

    REM Run Script 7: Brings all things together
    echo Running Script 7...
    python finalizer.py "%%f"

    REM Run Script 8: Checks if something is going wrong with the batters
    echo Running Script 8...
    python checker.py "%%f"

    REM Run Script 9: Removes Batters
    echo Running Script 9...
    python batters_remover.py "%%f"

    REM Run Script 10: Normalizes everything
    echo Running Script 10...
    python normalizer.py "%%f"

    echo Done processing file: %%f

    @REM REM Rename the file by removing 'updated_' prefix if present
    @REM set "FILENAME=%%~nxf"
    @REM if "!FILENAME:~0,8!"=="final_updated_" (
    @REM     set "NEWNAME=!FILENAME:~8!"
    @REM     echo Renaming file to !NEWNAME!
    @REM     ren "%%f" "!NEWNAME!"
    @REM )
)

echo All files processed and renamed.
endlocal
