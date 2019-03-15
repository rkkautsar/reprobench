#!/bin/bash
#SBATCH --export=all
#SBATCH --array=$run_ids
#SBATCH --mem=$mem
#SBATCH --time=$time

srun -- $python_path -m reprobench.runners.slurm.slurm_worker -c $config_path -d $db_path $SLURM_ARRAY_TASK_ID
