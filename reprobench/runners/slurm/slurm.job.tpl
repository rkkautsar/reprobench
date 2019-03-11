#!/bin/bash
#SBATCH --export=PYTHONPATH=.

module load $conda_module
srun $python_prefix/python -m reprobench.runners.slurm.slurm_worker -c $config_path -d $db_path $SLURM_ARRAY_TASK_ID
