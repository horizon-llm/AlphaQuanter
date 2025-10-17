#!/usr/bin/env bash

set -xeuo pipefail


wandb_api_key=YOUR_WANDB_API_KEY
wandb_entity=YOUR_WANDB_ENTITY
wandb_project=PROJECT_NAME

clip=0.1
kl=0.05
exp_name=exp_name
llm=Qwen2.5-7B-Instruct
dataset_name=dataset
entropy_coeff=0
train_batch_size=32
ppo_mini_batch_size=16
n_resp_per_prompt=16
epochs=5
save_freq=6
test_freq=6
infer_tp=2
train_sp=4

cuda_visible_devices=0,1,2,3,4,5,6,7
gpus_per_node=8
nnodes=1
ray_num_nodes=1

export WANDB_API_KEY=$wandb_api_key
export WANDB_ENTITY=$wandb_entity
export WANDB_PROJECT=$wandb_project
export CUDA_VISIBLE_DEVICES=$cuda_visible_devices
export GPUS_PER_NODE=$gpus_per_node
export NNODES=$nnodes
export RAY_NUM_NODES=$ray_num_nodes


total_gpus=$((gpus_per_node * nnodes))
if [ "$total_gpus" -lt 2 ]; then
  echo "Error: at least 2 GPUs are required, detected $total_gpus." >&2
  exit 1
fi

echo "Using $nnodes nodes and $gpus_per_node GPUs per node..."

hdfs_root=${PWD}
data_root=${PWD}
dataset_name=$dataset_name
model_path=$data_root/../models/$llm

if [ ! -d "$data_root/../models/$llm" ]; then
    hf download Qwen/"$llm" --local-dir "$data_root/../models/$llm"
fi

train_files=$data_root/data/$dataset_name/train.parquet
test_files=$data_root/data/$dataset_name/test.parquet
agent_loop_config_path=$data_root/recipe/langgraph_agent/stock_trading/agent.yaml

# wandb configuration
project_name=$wandb_project

# algorithm parameters
adv_estimator=grpo
use_kl_in_reward=false
kl_coef=0.0
use_kl_loss=true
kl_loss_coef=$kl
entropy_coeff=$entropy_coeff
clip_ratio_low=$clip
clip_ratio_high=$clip

max_turns=32
max_prompt_length=3072
max_response_length=16384
actor_lr=1e-6

train_batch_size=$train_batch_size
ppo_mini_batch_size=$ppo_mini_batch_size
n_resp_per_prompt=$n_resp_per_prompt
n_resp_per_prompt_val=1
epochs=$epochs
save_freq=$save_freq
test_freq=$test_freq

experiment_name=${exp_name}
default_local_dir=$data_root/checkpoint/$experiment_name


export RAY_LOGGING_LEVEL=DEBUG
export HYDRA_FULL_ERROR=1

export NCCL_IBEXT_DISABLE=1
export NCCL_NVLS_ENABLE=1
export NCCL_IB_HCA=mlx5
export UCX_NET_DEVICES=mlx5_0:1,mlx5_1:1,mlx5_2:1,mlx5_3:1,mlx5_4:1,mlx5_5:1,mlx5_6:1,mlx5_7:1
export VLLM_USE_V1=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

infer_tp=$infer_tp
train_sp=$train_sp
offload=true

actor_max_token_len_per_gpu=$max_response_length
log_prob_max_token_len_per_gpu=$max_response_length

train_files_param="['$train_files']"
test_files_param="['$test_files']"

python3 -m verl.trainer.main_ppo \
    algorithm.adv_estimator=$adv_estimator \
    algorithm.use_kl_in_reward=$use_kl_in_reward \
    algorithm.kl_ctrl.kl_coef=$kl_coef \
    data.train_files="$train_files_param" \
    data.val_files="$test_files_param" \
    data.return_raw_chat=true \
    data.train_batch_size=$train_batch_size \
    data.max_prompt_length=$max_prompt_length \
    data.max_response_length=$max_response_length \
    data.filter_overlong_prompts=true \
    data.truncation='error' \
    actor_rollout_ref.model.path="$model_path" \
    actor_rollout_ref.model.use_remove_padding=true \
    actor_rollout_ref.model.enable_gradient_checkpointing=true \
    actor_rollout_ref.actor.use_kl_loss=$use_kl_loss \
    actor_rollout_ref.actor.kl_loss_coef=$kl_loss_coef \
    actor_rollout_ref.actor.clip_ratio_low=$clip_ratio_low \
    actor_rollout_ref.actor.clip_ratio_high=$clip_ratio_high \
    actor_rollout_ref.actor.clip_ratio_c=3 \
    actor_rollout_ref.actor.optim.lr=$actor_lr \
    actor_rollout_ref.actor.entropy_coeff=$entropy_coeff \
    actor_rollout_ref.actor.use_dynamic_bsz=true \
    actor_rollout_ref.actor.ppo_mini_batch_size=$ppo_mini_batch_size \
    actor_rollout_ref.actor.ppo_max_token_len_per_gpu=$actor_max_token_len_per_gpu \
    actor_rollout_ref.actor.ulysses_sequence_parallel_size=$train_sp \
    actor_rollout_ref.actor.fsdp_config.param_offload=$offload \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=$offload \
    actor_rollout_ref.ref.log_prob_max_token_len_per_gpu=$log_prob_max_token_len_per_gpu \
    actor_rollout_ref.rollout.name=vllm \
    actor_rollout_ref.rollout.mode=async \
    actor_rollout_ref.rollout.tensor_model_parallel_size=$infer_tp \
    actor_rollout_ref.rollout.multi_turn.max_user_turns=$max_turns \
    actor_rollout_ref.rollout.multi_turn.max_assistant_turns=$max_turns \
    actor_rollout_ref.rollout.multi_turn.format=hermes \
    actor_rollout_ref.rollout.agent.agent_loop_config_path=$agent_loop_config_path \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.9 \
    actor_rollout_ref.rollout.n=$n_resp_per_prompt \
    actor_rollout_ref.rollout.val_kwargs.top_p=0.6 \
    actor_rollout_ref.rollout.val_kwargs.temperature=1.0 \
    actor_rollout_ref.rollout.val_kwargs.n=$n_resp_per_prompt_val \
    trainer.logger='["console","wandb"]' \
    trainer.project_name=$project_name \
    trainer.validation_data_dir=$data_root/valid_dump_$experiment_name \
    trainer.experiment_name=$experiment_name \
    trainer.n_gpus_per_node="$gpus_per_node" \
    trainer.val_before_train=true \
    trainer.log_val_generations=50 \
    trainer.nnodes="$nnodes" \
    trainer.save_freq=$save_freq \
    trainer.default_local_dir="$default_local_dir" \
    trainer.test_freq=$test_freq \
    trainer.total_epochs=$epochs "$@" \
    custom_reward_function.path=$data_root/recipe/langgraph_agent/stock_trading/my_reward_fn.py \
    custom_reward_function.name=new_reward_fn