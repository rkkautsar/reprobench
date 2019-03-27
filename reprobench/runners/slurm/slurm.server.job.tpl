#!/bin/bash
#SBATCH --export=all
#SBATCH -o $output_dir/slurm-run_%a.out

srun -- $python_path \
    -m reprobench.runners.slurm.server \
    -c $config_path \
    -d $db_path \
    $server_address \
