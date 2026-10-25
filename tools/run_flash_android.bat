@echo off
title Flashing Custom Android TV to USB Flashdisk
color 0A
echo ========================================================
echo  Flashing Custom Android TV to Partition 2 (PhysicalDrive2)
echo ========================================================
echo.
"C:\Users\trefeon\AppData\Local\Programs\Python\Python314\python.exe" -u "D:/github_repo/STB_B860H/tools/flash_android_p2.py"
echo.
echo ========================================================
echo  Flashing Complete! Press any key to exit.
echo ========================================================
pause
