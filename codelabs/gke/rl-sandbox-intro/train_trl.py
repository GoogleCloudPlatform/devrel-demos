import ray
from k8s_agent_sandbox import SandboxClient
from k8s_agent_sandbox.models import SandboxDirectConnectionConfig
from trl import GRPOConfig, GRPOTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
import urllib.request
import re

ray.init(ignore_reinit_error=True)

# 1. Define the Ray remote evaluation function
@ray.remote(num_cpus=0.1)
def evaluate_rollout(code, prompt_data):
    client = SandboxClient(connection_config=SandboxDirectConnectionConfig(api_url="http://sandbox-router.default.svc.cluster.local:8080"))
    
    # Claim a pre-warmed sandbox instantly based on the repo
    repo = prompt_data.get("repo")
    
    # In a full system, you'd route to different warmpools based on repo
    # Here we default to django for our single task
    sandbox = client.create_sandbox(
        template="swe-bench-django",
        warmpool="swe-bench-django-warmpool",
        sandbox_ready_timeout=600
    )
    
    try:
        # Check if the code is correctly formatted
        bash_match = re.search(r"```bash\n(.*?)\n```", code, re.DOTALL)
        if not bash_match:
            return 0.0
            
        script = bash_match.group(1)

        # In a real environment, we would apply the base commit and install here
        # For simplicity, we just execute the script
        import shlex
        script_cmd = f"bash -c {shlex.quote(script)}"
        result = sandbox.commands.run(script_cmd, timeout=60)
        
        # Calculate continuous reward based on test passage ratio
        if result.exit_code == 0:
            return 1.0
        
        # Very simple heuristic reward
        return 0.1
        
    finally:
        # Clean up and release the sandbox back to the pool
        client.delete_sandbox(sandbox.claim_name)

# 2. Define the Reward Function for TRL
def sandbox_reward_func(prompts, completions, **kwargs):
    # Dispatch evaluation to Ray cluster
    futures = [
        evaluate_rollout.remote(completion, {
            "repo": kwargs.get('repo', [])[i] if 'repo' in kwargs else None,
            "base_commit": kwargs.get('base_commit', [])[i] if 'base_commit' in kwargs else None
        }) for i, completion in enumerate(completions)
    ]
    
    # Block and wait for all sandbox evaluations to complete
    rewards = ray.get(futures)
    return rewards

# 3. Setup GRPO Trainer
@ray.remote(num_gpus=1, num_cpus=8)
def train():
    # Load dataset
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    # Filter to our selected target issue
    dataset = dataset.filter(lambda x: x["instance_id"] == "django__django-15388")
    
    def format_dataset(example):
        files = re.findall(r'^\+\+\+ b/(.+)$', example["patch"], re.MULTILINE)
        target_file = files[0] if files else ""
        
        file_content = ""
        if target_file:
            try:
                github_repo = example["repo"]
                url = f"https://raw.githubusercontent.com/{github_repo}/{example['base_commit']}/{target_file}"
                with urllib.request.urlopen(url) as response:
                    file_content = response.read().decode('utf-8')
            except Exception as e:
                pass
                
        prompt = f"""You are an expert software engineer.
You are given a GitHub issue and the content of the file that contains the bug.
Write an executable bash script that will modify the target file to fix the bug (e.g. using cat << 'EOF' > {target_file} or inline python edits).
Wrap your bash script in ```bash ... ``` tags. Do not output raw python code directly.

Target File: {target_file}

Original File Content:
```python
{file_content}
```

Issue:
{example['problem_statement']}
"""
        return {
            "prompt": prompt,
            "repo": example["repo"],
            "instance_id": example["instance_id"],
            "base_commit": example["base_commit"],
        }
        
    dataset = dataset.map(format_dataset)

    model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    training_args = GRPOConfig(
        output_dir="outputs",
        learning_rate=5e-6,
        max_steps=10,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        num_generations=8,
        generation_batch_size=8,
    )

    trainer = GRPOTrainer(
        model=model_name,
        processing_class=tokenizer,
        reward_funcs=[sandbox_reward_func],
        args=training_args,
        train_dataset=dataset,
    )

    print("Starting GRPO training with GKE Agent Sandboxes...")
    trainer.train()

def main():
    print("Submitting training job to GPU worker...")
    ray.get(train.remote())

if __name__ == "__main__":
    main()
