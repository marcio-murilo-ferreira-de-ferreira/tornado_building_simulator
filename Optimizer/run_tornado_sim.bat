@echo off
cd /d "%~dp0"
echo Iniciando o simulador... por favor, aguarde.

:: Encerrar portas velhas pro caso de reabertura
for /f "tokens=5" %%a in ('netstat -aon ^| find ":4179" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":4175" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

:: Iniciar Servidor do React Grafico na Porta 4179 em Background (Multi-Thread)
start /b cmd /c "python serve_dist.py >nul 2>&1"

:: Iniciar Servidor de Dados do React na Porta 4175 em Background
start /b cmd /c "python cors_server.py >nul 2>&1"

:: Iniciar Servidor Streamlit Principal
start /b streamlit run interactive_sim_ui.py --server.port 8501 --server.headless true
timeout /t 5 /nobreak > nul
start /max msedge --new-window --start-maximized http://localhost:8501
exit
