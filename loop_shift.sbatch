#!/bin/bash
#SBATCH -J Dovekie 
#SBATCH -N 1
#SBATCH -c 1
#SBATCH -t 00:20:00
#SBATCH --mem=1G

# Run all values between 1 and 149; limit to 50 concurrent tasks
#SBATCH --array=1-150%50

#SBATCH -o logs/%x_%A_%a.out
#SBATCH -e logs/%x_%A_%a.err


source ~/.bashrc
conda activate DOV_INT
SHIFT="${SLURM_ARRAY_TASK_ID}"
python3 filter_character_PS1.py --SURVEY 19 --SHIFT "-${SHIFT}"
