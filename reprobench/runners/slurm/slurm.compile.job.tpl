#!/bin/bash
#SBATCH --export=all

srun -- $python_path -m reprobench.runners.slurm.slurm_worker compile -c $config_path -d $db_path
