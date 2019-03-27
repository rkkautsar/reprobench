#!/bin/bash
#SBATCH --export=all
#SBATCH --array=$run_ids
#SBATCH --mem=$mem
#SBATCH --time=$time
#SBATCH -o $output_dir/slurm-server.out

srun -- $python_path \
    -m reprobench.runners.slurm.worker \
    -c $config_path \
    -d $db_path \
    $server_address \
    $SLURM_ARRAY_TASK_ID
