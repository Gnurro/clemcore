#!/bin/bash
# Usage: ./pipeline_huggingfaces.sh
# Preparation: ./setup_hf.sh
export HUGGINGFACE_HUB_CACHE=/data/jordan/huggingface_cache
export CUDA_VISIBLE_DEVICES=0,1
# activate HF venv:
source venv_hf/bin/activate
source prepare_path.sh
# run pipeline:
echo
echo "==================================================="
echo "PIPELINE: Starting"
echo "==================================================="
echo
game_runs=(
  # Single-player: adventuregame
  "adventuregame Qwen1.5-72B-Chat"
  "adventuregame Qwen2-72B-Instruct"
  "adventuregame openchat_3.5"
)
total_runs=${#game_runs[@]}
echo "Number of benchmark runs: $total_runs"
current_runs=1
for run_args in "${game_runs[@]}"; do
  echo "Run $current_runs of $total_runs: $run_args"
  bash -c "./run.sh ${run_args}"
  ((current_runs++))
done
echo "==================================================="
echo "PIPELINE: Finished"
echo "==================================================="