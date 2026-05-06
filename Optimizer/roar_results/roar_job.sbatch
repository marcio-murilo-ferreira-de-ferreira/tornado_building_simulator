#!/bin/bash
#SBATCH --job-name=tornado_retrofit
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem=16GB
#SBATCH --time=02:00:00
#SBATCH --output=abaqus_batch_%j.log
#SBATCH --error=abaqus_batch_%j.err

echo "=========================================================="
echo "Starting Tornado Retrofit HPC Job on Penn State Roar"
echo "Date: $(date)"
echo "Directory: $PWD"
echo "=========================================================="

# 1. Carregar modulo do Abaqus (Padrão no Roar)
module load abaqus

# Entrar no diretorio de trabalho
mkdir -p ~/tornado_sim_scratch
cd ~/tornado_sim_scratch

# 2. Gerar arquivos .inp (Input files) a partir dos scripts Python enviados via SFTP
echo "Generating Abaqus Input files (.inp) from .py scripts..."
for py_file in abaqus_run_*.py; do
    if [ -f "$py_file" ]; then
        echo "Processing $py_file..."
        abaqus cae noGUI=$py_file
    fi
done

# 3. Rodar os Solvers para todos os Inputs Encontrados
echo "Starting Abaqus Solvers..."
for inp_file in retrofit_*.inp; do
    if [ -f "$inp_file" ]; then
        job_name="${inp_file%.*}"
        echo "Submitting Abaqus Job: $job_name"
        # interactive flag holds the script until job finishes so we can loop
        abaqus job=$job_name input=$inp_file interactive ask_delete=OFF cpus=$SLURM_NTASKS
    fi
done

echo "=========================================================="
echo "All Abaqus simulations completed!"
echo "Date: $(date)"
echo "=========================================================="
