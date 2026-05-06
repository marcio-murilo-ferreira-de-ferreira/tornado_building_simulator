import streamlit as st
import subprocess
import os
import webbrowser
import glob

from forensic_retrofit_optimizer import calculate_design_uplift, main as run_optimizer
import importlib
import roar_ssh_client
importlib.reload(roar_ssh_client)
from roar_ssh_client import RoarSSHClient

import generate_slurm_job

st.set_page_config(
    page_title="Tornado Retrofit Simulation",
    page_icon="🌪️",
    layout="wide"
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Force actual full width and elegant padding robustly */
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 1rem;
    }
    [data-testid="block-container"] {
        max-width: 95vw !important;
        padding-top: 1rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    
    /* Elegant Frame Container styling for Streamlit Columns */
    .card-container {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 2.0rem 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
        height: 100%;
    }
    
    .stButton>button {
        width: 100%;
        background-color: #ef4444;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 1.40rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        margin-top: 10px;
        border: none;
        box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2);
    }
    .stButton>button:hover {
        background-color: #dc2626;
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(220, 38, 38, 0.3);
    }
    .stButton>button:active {
        transform: scale(0.96) translateY(0);
        box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
        background-color: #b91c1c;
    }
    
    /* SUPERIOR UPLIFT READABILITY */
    .metric-value {
        font-size: 3.5rem;
        font-weight: 800;
        color: #ef4444;
        line-height: 1.1;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
    }
    .metric-label {
        font-size: 1.5rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 76px !important;
    }
    
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #ef4444, #f87171);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }
    
    /* Increase Global Font Sizes Exuberantly for Wide Screens */
    p, label, .stMarkdown, .st-emotion-cache-16idsys p {
        font-size: 1.25rem !important;
        font-weight: 500;
        color: #334155;
    }
    
    /* Modern Neumorphic Sliders - Red Theme */
    .stSlider {
        margin-top: 5px;
        margin-bottom: 20px;
        padding-top: 35px !important; 
    }
    .stSlider [data-baseweb="slider"] {
        margin-top: 25px !important;
    }
    
    /* The Slider Track (Rail and Fill) */
    div[data-baseweb="slider"] > div > div:first-child {
        height: 10px !important;
        border-radius: 8px;
        background: #e2e8f0;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }
    .stSlider > div > div > div > div {
        height: 10px !important;
        background: linear-gradient(90deg, #ef4444, #dc2626) !important;
        box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
    }
    
    /* The thumb (Bolinha) */
    div[data-baseweb="slider"] [role="slider"] {
        width: 28px !important;
        height: 28px !important;
        background-color: #ffffff !important;
        border: 2px solid #dc2626 !important;
        border-radius: 50% !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1) !important;
        margin-top: -1px !important; 
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    div[data-baseweb="slider"] [role="slider"]:hover {
        transform: scale(1.15);
        box-shadow: 0 6px 8px -1px rgba(220, 38, 38, 0.3), 0 4px 6px -1px rgba(220, 38, 38, 0.2) !important;
    }
    
    /* Number Text */
    .stSlider div[data-testid="stThumbValue"], 
    .stSlider div[role="slider"] > div {
        position: absolute !important;
        top: -45px !important; 
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
        background: transparent !important;
        padding-bottom: 10px !important;
    }
    div[data-testid="stTickBarMax"], div[data-testid="stTickBarMin"], div.st-af {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
    }
    
    /* Input wrappers (caixas sombreadas) */
    .stSelectbox > div > div, .stNumberInput > div > div, .stTextInput > div > div {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease;
    }
    .stSelectbox > div > div:focus-within, .stNumberInput > div > div:focus-within, .stTextInput > div > div:focus-within {
        border-color: #ef4444 !important;
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2) !important;
    }
    
    .terminal-output {
        font-family: 'Courier New', Courier, monospace;
        background-color: #0f172a;
        color: #ffffff !important;
        padding: 1.5rem;
        border-radius: 8px;
        white-space: pre-wrap;
        border: 1px solid #1e293b;
        margin-top: -0.5rem;
        font-size: 1.15rem;
        line-height: 1.5;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Force child paragraph elements to inherit white color against Streamlit global overrides */
    .terminal-output p, .terminal-output span, .terminal-output div {
        color: #ffffff !important;
        text-shadow: 0 0 3px rgba(255,255,255,0.8) !important;
    }
    
    /* Annihilate empty space blocks and alert placeholders */
    .element-container:empty, div[data-testid="stEmpty"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    .streamlit-expanderHeader { margin-top: 0; }
    div[data-testid="stVerticalBlock"] > div:first-child { padding-top: 0 !important; margin-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🌪️ Tornado Retrofit Parameters")
st.markdown("Modify the simulation inputs and visualize the design uplift instantly.")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("⚙️ Inputs Configuration")
    
    # Interactive Sliders for Input
    span = st.slider("Span (ft)", min_value=10.0, max_value=80.0, value=40.0, step=1.0)
    spacing = st.slider("Joist Spacing (in)", min_value=12.0, max_value=48.0, value=16.0, step=1.0)
    wind_speed = st.slider("Wind Speed (mph)", min_value=90.0, max_value=250.0, value=135.0, step=1.0)
    
    # Hide the seed input so it's small and not obvious
    seed_col1, seed_col2 = st.columns([1, 2])
    with seed_col1:
        seed_val = st.number_input("Genetic Engine Seed", min_value=0, max_value=9999, value=7, step=1)
    
    # Live Calculation 
    st.markdown("<br>", unsafe_allow_html=True)
    res = calculate_design_uplift(span, spacing, wind_speed)
    uplift_lbf = res["force_lbf"]
    uplift_n = res["force_n"]
    
    st.markdown("<div class='metric-label'>Design Uplift Demand</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{uplift_lbf:,.1f} lbf</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #888; font-size: 0.9rem;'>{uplift_n:,.1f} Newtons</p>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- HPC CONNECTION EXPANDER ---
    run_roar_button = False
    with st.expander("🎓 Penn State Roar HPC Connection", icon="🌩️"):
        st.markdown("<p style='font-size: 1.1rem; color: #555;'>Enter your credentials to bypass manual downloads and push directly to <code>submit.hpc.psu.edu</code>. <b>Aprove o DUO no seu celular (Push).</b></p>", unsafe_allow_html=True)
        roar_user = st.text_input("Penn State Access ID")
        roar_pass = st.text_input("Password", type="password")
        run_roar_button = st.button("🚀 Push to Roar HPC & Run", type="primary", use_container_width=True)

    # --- MANUAL ZIP EXPORT FALLBACK ---
    generate_package = False
    with st.expander("📦 Manual OOD ZIP Export (Fallback)", icon="🥡"):
        st.markdown("<p style='font-size: 1.1rem; color: #555;'>If the automated SSH connection fails, generate a ZIP package for manual upload via <b>Open OnDemand</b>.</p>", unsafe_allow_html=True)
        generate_package = st.button("📦 Generate Roar ZIP Package", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button("🚀 Run Local Optimizer (Mockup)")

with col2:
    st.subheader("📊 Output Console")
    
    # Initialize session state for persistence
    if "sim_complete" not in st.session_state:
        st.session_state.sim_complete = False
        st.session_state.last_result = ""
    # Tracker session states
    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = None
    if "roar_user" not in st.session_state:
        st.session_state.roar_user = ""
    if "roar_pass" not in st.session_state:
        st.session_state.roar_pass = ""

    # Helper function to update Streamlit UI during MFA
    def mfa_wait_callback():
        st.warning("🟡 **CHECK YOUR PHONE!** Aprove o aviso do DUO PUSH no celular para liberar a conexão...", icon="📱")

    if run_roar_button:
        if not roar_user or not roar_pass:
            st.error("❌ Digite o seu ID da Penn State (Acesso) e sua Senha no painel HPC para conectar.")
        else:
            with st.spinner("Conectando ao Penn State Roar Supercomputer (Aguardando Desafio DUO)..."):
                client = RoarSSHClient(roar_user, roar_pass)
                success, msg = client.connect(mfa_callback=mfa_wait_callback)
                
                if success:
                    st.success(f"🔓 {msg} - Autenticado.")
                    st.info("Gerando arquivos paramétricos do Abaqus localmente...")
                    # 1. Run local optimizer
                    run_optimizer(span_ft=span, spacing_in=spacing, wind_speed_mph=wind_speed, seed=seed_val)
                    subprocess.run(["python", "generate_abaqus_batch.py"], capture_output=True, text=True)
                    
                    # 2. Build SBATCH file
                    sbatch_file = generate_slurm_job.create_sbatch_file()
                    
                    st.info("Empacotando simulações em ZIP único e transferindo via túnel rápido (Por favor aguarde)...")
                    # 3. Handle SSH upload (Single ZIP File Strategy to prevent EOFError / Anti-DDoS blocking)
                    remote_dir = "tornado_sim_scratch"
                    client.exec_command(f"mkdir -p {remote_dir}")
                    
                    import zipfile
                    zip_filename = "roar_bundle.zip"
                    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(sbatch_file)
                        for py_file in glob.glob("abaqus_run_*.py"):
                            zipf.write(py_file)
                            
                    # Tenta subir APENAS o ZIP de forma contínua
                    upload_success, upload_msg = client.upload_file(zip_filename, f"{remote_dir}/{zip_filename}")
                    
                    if not upload_success:
                        st.error(f"❌ Falha no Upload do ZIP: {upload_msg}")
                        result_text = f"========================================================\nROAR HPC UPLOAD FAILED\n{upload_msg}\n========================================================"
                    else:
                        st.info("Descompactando pacotes remotamente e Submetendo Jobs na fila do Roar SLURM...")
                        client.exec_command(f"cd {remote_dir} && unzip -o {zip_filename}")
                        
                        # 4. Execute standard job submission from within the scratch folder
                        job_success, job_msg = client.exec_command(f"cd {remote_dir} && sbatch {sbatch_file}")
                        
                        if job_success:
                            import re
                            match = re.search(r'job (\d+)', job_msg)
                            if match:
                                st.session_state.active_job_id = match.group(1)
                                st.session_state.roar_user = roar_user
                                st.session_state.roar_pass = roar_pass
                            result_text = f"========================================================\nROAR HPC JOB SUBMITTED SUCCESSFULLY\nTarget: submit.hpc.psu.edu\nDirectory: ~/{remote_dir}\nSlurm Response:\n{job_msg}\n========================================================"
                        else:
                            result_text = f"========================================================\nROAR HPC JOB SUBMISSION FAILED\nError:\n{job_msg}\n========================================================"

                    
                    client.close()
                    
                    st.session_state.sim_complete = True
                    st.session_state.last_result = result_text
                    st.rerun()
                else:
                    st.error(f"❌ Conexão Falhou: {msg}")

    elif generate_package:
        with st.spinner("📦 Empacotando Abaqus Scripts e SBATCH em um arquivo ZIP..."):
            try:
                st.info("Gerando arquivos paramétricos Otimizados localmente...")
                # 1. Run local optimizer
                run_optimizer(span_ft=span, spacing_in=spacing, wind_speed_mph=wind_speed, seed=seed_val)
                subprocess.run(["python", "generate_abaqus_batch.py"], capture_output=True, text=True)
                
                # 2. Build SBATCH file
                sbatch_file = generate_slurm_job.create_sbatch_file()
                
                # 3. Create ZIP Archive in Memory
                st.info("Compactando pacote de submissão...")
                import io
                import zipfile
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(sbatch_file, f"tornado_sim_scratch/{sbatch_file}")
                    for py_file in glob.glob("abaqus_run_*.py"):
                        zip_file.write(py_file, f"tornado_sim_scratch/{py_file}")
                
                # Setup Download
                st.session_state.zip_bytes = zip_buffer.getvalue()
                st.session_state.zip_ready = True
                
                st.success("✅ Pacote Roar ZIP gerado com sucesso!")
                result_text = "========================================================\nROAR HPC PACKAGE GENERATED SUCCESSFULLY\nInstructions:\n1. Download the ZIP file using the button below.\n2. Open https://portal.hpc.psu.edu (Open OnDemand).\n3. Upload to your scratch folder and extract.\n4. Run command: sbatch roar_job.sbatch\n========================================================"
                st.session_state.sim_complete = True
                st.session_state.last_result = result_text
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao empacotar arquivos: {str(e)}")

    if st.session_state.get("zip_ready", False):
        st.download_button(
            label="⬇️ Download 'roar_submission.zip'",
            data=st.session_state.zip_bytes,
            file_name="roar_submission.zip",
            mime="application/zip",
            type="primary"
        )

    elif run_button:
        with st.spinner("Running genetic algorithm and evaluating retrofits..."):
            try:
                # 1. Run Optimizer via imported python logic
                result_text = run_optimizer(span_ft=span, spacing_in=spacing, wind_speed_mph=wind_speed, seed=seed_val)
                
                # Write to the roar_interactive log so that build_dashboard works too
                with open("roar_interactive_run.log", "w", encoding="utf-8") as f:
                    f.write(result_text)
                    
                # 2. Re-trigger Abaqus generation in the background just to keep files sync'd 
                subprocess.run(["python", "generate_abaqus_batch.py"], capture_output=True, text=True)
                
                # 3. Trigger Dashboard Build
                subprocess.run(["python", "build_dashboard.py"], capture_output=True, text=True)
                
                # Update session state
                st.session_state.sim_complete = True
                st.session_state.last_result = result_text
                st.rerun() # Ensure the UI updates to show persistent state
                
            except Exception as e:
                st.error(f"Error during execution: {str(e)}")
                
    if st.session_state.get("active_job_id"):
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📡 Roar HPC Receiving Station (LIVE)", expanded=True, icon="📡"):
            st.markdown(f"<p style='color: #4CAF50;'><b>Tracking Active SIM:</b> Job <code>{st.session_state.active_job_id}</code></p>", unsafe_allow_html=True)
            st.info("Ping the Roar Supercomputer. When COMPLETED, results will be forcefully downloaded.", icon="ℹ️")
            if st.button("🔄 PING & Fetch Results", type="primary", use_container_width=True):
                with st.spinner(f"📡 Pinging SLURM Queue for Job {st.session_state.active_job_id}..."):
                    client = RoarSSHClient(st.session_state.roar_user, st.session_state.roar_pass)
                    c_success, c_msg = client.connect(mfa_callback=mfa_wait_callback)
                    if c_success:
                        j_success, is_running, j_status = client.check_job_status(st.session_state.active_job_id)
                        if j_success:
                            if is_running:
                                st.warning(f"⏳ The Job is currently: **{j_status}**. Please wait for completion on the supercomputer.")
                            else:
                                st.success("🎉 Job Completed! Initializing Reverse B64 Tunnel download...")
                                with st.spinner("Silently downloading massive Reports and ODB packages..."):
                                    d_success, d_msg = client.download_results_b64("tornado_sim_scratch", "roar_results.zip")
                                    if d_success:
                                        import zipfile
                                        with zipfile.ZipFile("roar_results.zip", 'r') as z:
                                            z.extractall("roar_results")
                                        st.success("🛰️ Download Finished! The reverse tunnel has securely extracted 3D data.")
                                        st.session_state.active_job_id = None
                                        st.session_state.last_result = "========================================================\nROAR HPC RESULTS DOWNLOADED SUCCESSFULLY\nResults extracted to local 'roar_results' folder.\n========================================================"
                                        st.rerun()
                                    else:
                                        st.error(d_msg)
                        else:
                            st.error(f"Error checking status: {j_status}")
                        client.close()
                    else:
                        st.error(f"Error reconnecting to ROAR: {c_msg}")
    
    if st.session_state.sim_complete:
        st.markdown(f"<div class='terminal-output'>{st.session_state.last_result}</div>", unsafe_allow_html=True)
        st.success("✅ Simulation completed successfully!")
        
        # Parse the winner and save to JSON
        import re
        import json
        winner_strategy = "Unknown"
        params_dict = {}
        text = st.session_state.last_result
        if "Selected Strategy" in text:
            match = re.search(r"Selected Strategy ([A-Z]) \((.*?)\): (.*)", text)
            if match:
                winner_strategy = match.group(1)
                params_str = match.group(3)
                # Parse h=20.0 in, thk=0.300 in, etc.
                pairs = params_str.split(",")
                for pair in pairs:
                    if "=" in pair:
                        k, v = pair.split("=")
                        num_match = re.search(r'[0-9]+\.?[0-9]*', v)
                        if num_match:
                            params_dict[k.strip()] = float(num_match.group(0))
        
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.join(base_dir, "..", "3D_Builder", "winner_transfer.json")
        with open(target_path, "w") as f:
            json.dump({"strategy": winner_strategy, "parameters": params_dict}, f)
        
        st.markdown("<br>", unsafe_allow_html=True)
        colA, colB = st.columns(2)
        with colA:
            if st.button("📋 Open Full Visual Report", use_container_width=True):
                import webbrowser
                try:
                    subprocess.Popen(['start', '/max', 'msedge', '--new-window', '--start-maximized', 'http://localhost:4179/'], shell=True)
                except:
                    webbrowser.open_new('http://localhost:4179/')
            st.info("💡 The Visual Interface has started in the background. Click above to open!")
            
        with colB:
            # 3D Building Bridge Button
            link = "http://localhost:8502"
            button_html = f'''
            <a href="{link}" target="_blank" style="text-decoration: none;">
                <button style="
                    width: 100%;
                    background-color: #3b82f6;
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                    padding: 0.8rem 1rem;
                    font-size: 1.25rem;
                    cursor: pointer;
                    margin-top: 10px;
                    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
                " onmouseover="this.style.backgroundColor='#2563eb'; this.style.transform='translateY(-3px)'" 
                   onmouseout="this.style.backgroundColor='#3b82f6'; this.style.transform='translateY(0)'">
                    🏗️ Build 3D Model (Strategy {winner_strategy})
                </button>
            </a>
            '''
            st.markdown(button_html, unsafe_allow_html=True)
            st.success("✨ A estrutura de transferência foi salva! Abra o Prédio 3D.")
            
    else:
        st.info("👈 Adjust the sliders to see the live _Design Uplift_ calculation change. Click the run button to perform the genetic algorithm search with these values.")
    
    st.markdown("</div>", unsafe_allow_html=True)

