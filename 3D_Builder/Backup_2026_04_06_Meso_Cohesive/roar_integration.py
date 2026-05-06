import os
import time
from roar_ssh_client import RoarSSHClient

def create_sbatch_file(job_name, py_script_name, num_cpus=4):
    sbatch_content = f"""#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks={num_cpus}
#SBATCH --cpus-per-task=1
#SBATCH --mem=16GB
#SBATCH --time=02:00:00
#SBATCH --job-name={job_name}
#SBATCH --partition=open

module purge
module load abaqus/2022

# Step 1: Run CAE script to build model and generate .inp file (single CPU)
abaqus cae noGUI={py_script_name}

# Step 2: Run the actual Explicit solver in parallel using the generated .inp
if [ -f "MasonryWallJob_Final.inp" ]; then
    abaqus job=MasonryWallJob_Final cpus={num_cpus} mp_mode=mpi interactive
fi

# Step 3: Absolute Fail-Safe Error Extraction
# If Abaqus CAE crashed natively (no .inp) or the Job failed (no images), trick the Streamlit downloader
if [ ! -f "mises_result.png" ]; then
    echo "ABAQUS COMPLETELY ABORTED NATIVELY. DUMPING SLURM TRACEBACK:" > mises_result.png
    cat slurm-*.out >> mises_result.png 2>/dev/null
    echo "--- RPY LOG ---" >> mises_result.png
    cat abaqus.rpy >> mises_result.png 2>/dev/null
fi
"""
    return sbatch_content

def run_on_roar(psu_user, psu_pass, local_py_path, status_placeholder, log_container, monitor_container=None, num_cpus=4):
    job_name = "wall_sim"
    remote_base_dir = f"scratch/masonry_wall_sim_{int(time.time())}"
    py_filename = os.path.basename(local_py_path)
    
    # 1. Prepare local .sbatch
    sbatch_path = os.path.join(os.path.dirname(local_py_path), "sim.sbatch")
    with open(sbatch_path, "w", encoding="utf-8", newline='\n') as f:
        f.write(create_sbatch_file(job_name, py_filename, num_cpus=num_cpus))
        
    client = RoarSSHClient(psu_user, psu_pass)
    
    def mfa_cb():
        status_placeholder.warning("🔔 DUO PUSH: Please approve the Penn State login request on your phone!")
        
    success, msg = client.connect(mfa_callback=mfa_cb)
    
    if not success:
        return False, msg
        
    status_placeholder.success("✅ Secure connection established with Roar!")
    
    try:
        # 2. Upload Python script and SBATCH script
        log_container.write("Uploading files via B64 tunnel...")
        remote_py = f"{remote_base_dir}/{py_filename}"
        remote_sbatch = f"{remote_base_dir}/sim.sbatch"
        
        ok, um = client.upload_file(local_py_path, remote_py)
        if not ok: return False, um
        
        ok, um2 = client.upload_file(sbatch_path, remote_sbatch)
        if not ok: return False, um2
        
        # 3. Submit Job
        log_container.write("Submitting job to SLURM queue...")
        cmd = f"cd {remote_base_dir} && sbatch sim.sbatch"
        ok, sout = client.exec_command(cmd)
        
        if not ok:
            return False, f"Job submission failed: {sout}"
            
        try:
            job_id = "".join([c for c in sout if c.isdigit()])
            if not job_id:
                raise ValueError()
        except:
            return False, f"Could not parse SLA job ID from: {sout}"
            
        log_container.write(f"Job successfully submitted! SLURM ID: {job_id}")
        
        # 4. Monitor loop
        status_placeholder.info(f"⏳ Waiting for Roar execution (Job {job_id})... This may take several minutes depending on the supercomputer queue.")
        
        job_done = False
        start_time = time.time()
        
        while not job_done:
            time.sleep(10)
            
            if time.time() - start_time > 14400:
                return False, "Job timed out (4 hours no Streamlit Monitor)."
                
            ok, is_running, status_val = client.check_job_status(job_id)
            if not ok:
                log_container.write(f"Warning: Failed to parse job status. {status_val}")
                continue
                
            if not is_running:
                job_done = True
            else:
                log_container.write(f"SLURM Status: {status_val}")
                
            # --- LIVE ABAQUS MONITOR ---
            if monitor_container:
                # Silently catch the .sta file if it exists, grab last 15 lines of increment data
                ok_tail, tail_out = client.exec_command(f"tail -n 15 {remote_base_dir}/MasonryWallJob_Final.sta 2>/dev/null")
                if ok_tail and tail_out.strip():
                    monitor_container.code(f"--- ABAQUS LIVE MONITOR ---\n{tail_out.strip()}", language="plaintext")
                
        status_placeholder.success("✅ Job finished on the Roar cluster! Downloading result images...")
        time.sleep(5)
        
        # 5. Extract Images / ZIP from remote
        local_result_zip = os.path.join(os.path.dirname(local_py_path), "roar_results.zip")
        ok, dmsg = client.download_results_b64(remote_base_dir, local_result_zip)
        
        if not ok:
            return False, f"Failed to download results: {dmsg}"
            
        # Unzip locally
        import zipfile
        try:
            with zipfile.ZipFile(local_result_zip, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(local_py_path))
            return True, "Analysis and transfer completed successfully!"
        except Exception as e:
            return False, f"Failed to unpack zip: {str(e)}"
    finally:
        client.close()
