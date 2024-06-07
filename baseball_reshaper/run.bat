@echo off

REM Run Script 0: Check if Batters has less lines than Homeplate
echo Running Script 0...
for /f "delims=" %%i in ('python lines_checker.py %1') do set OUTPUT=%%i
REM Check if the output is "false" and break the execution if true
if "%OUTPUT%"=="false" (
    echo Homeplate is incomplete!
    exit /b 1
) else (
    echo Batters/Homeplate are ok. Check is done!
)
echo Continue the procedure

REM Run Script 1: Copy Batters to Homeplate tab
echo Running Script 1...
python batters_mover.py %1
echo Batters are inside Homeplate

REM Run Script 2: Creates the Inning column
echo Running Script 2...
python inning_creator.py %1
echo Innings are now ready

REM Run Script 3: Makes duration 1 in each line
echo Running Script 3...
python reshaper.py %1

REM Run Script 4: Concatanates Batters and Reshaped tab together
echo Running Script 4...
python concatanator.py %1

REM Run Script 5: Fills the gaps among players
echo Running Script 5...
python gap_filler.py %1

REM Run Script 6: Fills the gaps in the very beginning if necessary
echo Running Script 6...
python gap_start_filler.py %1

REM Run Script 7: Brings all things together
echo Running Script 7...
python finalizer.py %1

REM Run Script 8: Checks if something is going wrong with the batters
echo Running Script 8...
python checker.py %1

REM Run Script 9: Removes Batters
echo Running Script 9...
python batters_remover.py %1

REM Run Script 10: Normalizes everything
echo Running Script 10...
python normalizer.py %1