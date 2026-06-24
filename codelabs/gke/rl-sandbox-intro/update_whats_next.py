import re

file_path = "/google/src/cloud/drewbr/rl-sandbox-codelab/google3/third_party/devsite/codelabs/en/codelabs/gke/high-performance-distributed-rl-sandbox.lab.md"

with open(file_path, "r") as f:
    content = f.read()

whats_next = r"""### Time and Cost Guidelines

* **Overall Codelab Time:** ~30-45 minutes (mostly waiting for the GPU Node pool and Sandbox Images to build and deploy).
* **Training Job Time:** ~5-10 minutes. By modifying `max_steps=10` and `num_cpus=0.1` for `evaluate_rollout`, we ensure Ray parallelizes evaluations quickly so you don't incur hours of high-end GPU costs.

## What's Next?

This codelab laid the foundation for securely evaluating untrusted code in a distributed RL loop. Here's a preview of enhancements you can build on top of this architecture:

* **Pod Snapshots:** Instead of pre-installing dependencies at image-build time, you can create a baseline container, run heavy `pip install` or compilation steps, and then snapshot the memory state of the gVisor sandbox. Future evaluations can instantly clone this snapshot, skipping the setup phase completely.
* **Multiple Sandbox Images:** As demonstrated by the `repo = prompt_data.get("repo")` logic, you can deploy multiple `SandboxWarmPool` resources (one for Django, one for SymPy, one for Sphinx, etc.). The Sandbox Router will dynamically match Ray workers to the correct pre-warmed environment for the task.
* **Multi-Turn Rollouts:** We evaluated a single-turn bash script in this lab. Advanced RL agents use multi-turn execution (e.g., the model writes a script, executes it, reads the stdout, and writes a correction before final evaluation). The Sandbox Router supports persistent claim IDs that allow Ray workers to re-connect to the same Sandbox across multiple LLM generation steps.

### Clean up

To avoid incurring charges to your Google Cloud account for the resources used in this codelab:"""

content = content.replace("### Clean up\n\nTo avoid incurring charges to your Google Cloud account for the resources used in this codelab:", whats_next)

with open(file_path, "w") as f:
    f.write(content)

print("Whats next section added successfully!")
