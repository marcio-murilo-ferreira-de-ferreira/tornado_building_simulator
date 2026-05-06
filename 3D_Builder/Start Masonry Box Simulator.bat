@echo off
setlocal
color 0B
title Masonry Box Simulator (Explicit Dynamics 3D)

echo =======================================================
echo          MASONRY BOX SIMULATOR - PRO EDITION           
echo           Explicit 3D Dynamic Collapse (ROAR)          
echo =======================================================
echo.
echo Launching Streamlit Dashboard...
echo Keep this window open. Close it to stop the server.
echo.

cd /d "%~dp0"
python -m streamlit run app.py

pause
