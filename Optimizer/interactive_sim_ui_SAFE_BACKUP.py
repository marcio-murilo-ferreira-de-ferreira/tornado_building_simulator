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
    
    /* Fix alignment gaps from streamlit default elements */
    .streamlit-expanderHeader { margin-top: 0; }
    div[data-testid="stVerticalBlock"] > div:first-child { padding-top: 0 !important; margin-top: 0 !important; }
    
    /* Annihilate empty space blocks and alert placeholders */
    .element-container:empty, div[data-testid="stEmpty"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    
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
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 1.40rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        margin-top: 10px;
    }
    .stButton>button:hover {
        background-color: #ff2b2b;
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(255, 75, 75, 0.25);
    }
    .stButton>button:active {
        transform: scale(0.96) translateY(0);
        box-shadow: 0 2px 4px rgba(255, 75, 75, 0.3);
        background-color: #e51d1d;
    }
    
    /* SUPERIOR UPLIFT READABILITY */
    .metric-value {
        font-size: 3.5rem;
        font-weight: 800;
        color: #ff4b4b;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 1.5rem;
        font-weight: 600;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 76px !important; /* Move block down physically by ~2 centimeters */
    }
    
    h1 {
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #ff4b4b, #ff9090);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Increase Global Font Sizes Exuberantly for Wide Screens */
    p, label, .stMarkdown, .st-emotion-cache-16idsys p {
        font-size: 1.65rem !important;
    }
    
    /* Clean Windows-style typography and spacing for inputs */
    .stSlider {
        margin-top: 5px;
        margin-bottom: 20px;
        padding-top: 35px !important; /* Force space ABOVE the slider rail for numbers to breathe */
    }
    
    /* FIX: The Definitive Way to Lift the Red Numbers above the Streamlit Track */
    .stSlider [data-baseweb="slider"] {
        margin-top: 25px !important;
    }
    
    /* FIX: TORNADO SUPER JUMBO THICK SLIDERS! */
    /* 1. Make the Slider Track (Line) much thicker */
    .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] { display: none !important; }
    .stSlider [data-baseweb="slider"] > div > div > div {
        height: 12px !important; /* Thick lines */
        border-radius: 6px !important;
    }
    
    /* 2. Make the Thumb (Bolinha) Giant to Match! */
    .stSlider div[role="slider"] {
        width: 30px !important;
        height: 30px !important;
        border-radius: 50% !important;
        box-shadow: 0 4px 8px rgba(255, 75, 75, 0.4) !important;
        margin-top: -3px !important; /* Center the larger thumb along the thicker track */
    }
    
    /* 3. Deal with the number text positioning again since the track shifted */
    .stSlider div[data-testid="stThumbValue"], 
    .stSlider div[role="slider"] > div {
        position: absolute !important;
        top: -45px !important; /* Yank the number violently upwards */
        font-size: 1.35rem !important;
        font-weight: bold !important;
        background: transparent !important;
        padding-bottom: 10px !important;
    }
    
    .card-container {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
        height: 100%;
    }
    /* Fix alignment gaps from streamlit default elements */
    .streamlit-expanderHeader { margin-top: 0; }
    div[data-testid="stVerticalBlock"] > div:first-child { padding-top: 0 !important; margin-top: 0 !important; }
    
    /* Annihilate empty space blocks and alert placeholders */
    .element-container:empty, div[data-testid="stEmpty"] { display: none !important; height: 0 !important; margin: 0 !important; padding: 0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    
    .terminal-output {
        font-family: 'Courier New', Courier, monospace;
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 1.5rem;
        border-radius: 8px;
        white-space: pre-wrap;
        border: 1px solid #333;
        margin-top: -0.5rem;
        font-size: 1.15rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌪️ Tornado Retrofit Parameters")
st.markdown("Modify the simulation inputs and visualize the design uplift instantly.")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
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
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='card-container'>", unsafe_allow_html=True)
    st.subheader("📊 Output Console")
    
    # Initialize session state for persistence
    if "sim_complete" not in st.session_state:
        st.session_state.sim_complete = False
        st.session_state.last_result = ""

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
    
    if st.session_state.sim_complete:
        st.markdown(f"<div class='terminal-output'>{st.session_state.last_result}</div>", unsafe_allow_html=True)
        st.success("✅ Simulation completed successfully!")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📋 Open Full Visual Report"):
            import webbrowser
            try:
                subprocess.Popen(['start', '/max', 'msedge', '--new-window', '--start-maximized', 'http://localhost:4179/'], shell=True)
            except:
                webbrowser.open_new('http://localhost:4179/')
        
        st.info("💡 A interface visual com React iniciou em background no launcher. Clique acima para abrir!")
    else:
        st.info("👈 Adjust the sliders to see the live _Design Uplift_ calculation change. Click the run button to perform the genetic algorithm search with these values.")
    
    st.markdown("</div>", unsafe_allow_html=True)
