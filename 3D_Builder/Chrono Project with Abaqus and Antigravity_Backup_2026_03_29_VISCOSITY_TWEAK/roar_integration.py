import os
import time
from roar_ssh_client import RoarSSHClient

def create_sbatch_file(job_name, py_script_name):
    sbatch_content = f"""#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=8GB
#SBATCH --time=01:00:00
#SBATCH --job-name={job_name}
#SBATCH --partition=open

module purge
module load abaqus/2022

# Run Abaqus without GUI
abaqus cae noGUI={py_script_name}
"""
    return sbatch_content

def run_on_roar(psu_user, psu_pass, local_py_path, status_placeholder, log_container):
    job_name = "wall_sim"
    remote_base_dir = f"scratch/masonry_wall_sim_{int(time.time())}"
    py_filename = os.path.basename(local_py_path)
    
    # 1. Prepare local .sbatch
    sbatch_path = os.path.join(os.path.dirname(local_py_path), "sim.sbatch")
    with open(sbatch_path, "w", encoding="utf-8", newline='\n') as f:
        f.write(create_sbatch_file(job_name, py_filename))
        
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
            
            if time.time() - start_time > 3600:
                return False, "Job timed out (1 hour)."
                
            ok, is_running, status_val = client.check_job_status(job_id)
            if not ok:
                log_container.write(f"Warning: Failed to parse job status. {status_val}")
                continue
                
            if not is_running:
                job_done = True
            else:
                log_container.write(f"SLURM Status: {status_val}")
                
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
