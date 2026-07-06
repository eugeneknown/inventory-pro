@echo off
echo Building InventoryPRO...
pyinstaller build.spec --clean
echo.
echo Build complete! EXE is in dist\InventoryPRO\InventoryPRO.exe
pause
