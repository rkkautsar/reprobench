#!/bin/bash

module load $conda_module
source activate $conda_env
python -m reprobench.runners.slurm.slurm_worker -c $config -d $db_path $SLURM_ARRAY_TASK_ID
