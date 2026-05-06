@echo off
echo =======================================================
echo     TORNADO DUAL-DASHBOARD SYSTEM (OPTIMIZER + 3D)
echo =======================================================
echo Iniciando o Otimizador (Tela 1) na porta 8501...
start "" /B streamlit run "%~dp0Optimizer\interactive_sim_ui.py" --server.port 8501
timeout /t 3 >nul

echo Iniciando o Construtor 3D (Tela 2) na porta 8502 em background...
start "" /B streamlit run "%~dp03D_Builder\app.py" --server.port 8502

echo =======================================================
echo Ambientes ligados. O seu navegador principal abrira o 
echo Otimizador. A partir dele voce podera exportar o prediro
echo para a tela 3D.
echo =======================================================
pause
