@echo off

REM Run Script 1: Creates the Inning column
echo Running Script 1...
python inning_creator.py %1
echo Innings are now ready

REM Run Script 2: Makes duration 1 in each line
echo Running Script 2...
python reshaper.py %1

REM Run Script 3: Concatanates Batters and Reshaped tab together
echo Running Script 3...
python concatanator.py %1

REM Run Script 4: Fills the gaps among players
echo Running Script 4...
python gap_filler.py %1

REM Run Script 5: Fills the gaps in the very beginning if necessary
echo Running Script 5...
python gap_start_filler.py %1

REM Run Script 6: Brings all things together
echo Running Script 6...
python finalizer.py %1

