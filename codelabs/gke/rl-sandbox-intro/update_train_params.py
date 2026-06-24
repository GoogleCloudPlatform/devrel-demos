import re

file_path = "/usr/local/google/home/drewbr/Projects/RL-sandbox/codelab/train_trl.py"

with open(file_path, "r") as f:
    content = f.read()

# Update the CPU requirements for evaluate_rollout
content = content.replace("@ray.remote\ndef evaluate_rollout", "@ray.remote(num_cpus=0.1)\ndef evaluate_rollout")

# Update max_steps in GRPOConfig
content = content.replace("max_steps=50", "max_steps=10")

with open(file_path, "w") as f:
    f.write(content)

print("train_trl.py updated locally!")

file_path_piper = "/google/src/cloud/drewbr/rl-sandbox-codelab/google3/third_party/devsite/codelabs/en/codelabs/gke/high-performance-distributed-rl-sandbox.lab.md"

with open(file_path_piper, "r") as f:
    content = f.read()

content = content.replace("@ray.remote\ndef evaluate_rollout", "@ray.remote(num_cpus=0.1)\ndef evaluate_rollout")
content = content.replace("max_steps=50,", "max_steps=10,")

with open(file_path_piper, "w") as f:
    f.write(content)

print("Codelab updated in Piper!")
