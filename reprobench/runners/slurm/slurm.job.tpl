#!/bin/bash
#SBATCH --export=all

srun -- $python_path -m reprobench.runners.slurm.slurm_worker -c $config_path -d $db_path $SLURM_ARRAY_TASK_ID
