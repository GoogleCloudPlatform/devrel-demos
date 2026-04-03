# NeMo-RL GRPO GPU Demo

This sample demonstrates how to orchestrate a GPU-based [Ray](https://ray.io/) cluster on GKE using [XPK](https://github.com/google/xpk) and attach a high-performance Google Cloud Managed Service for Lustre array to run a NeMo-RL workload natively.

## Prerequisites
- A Google Cloud Project with Billing Enabled.
- `gcloud` CLI installed and authenticated.
- `xpk` tool installed (`pip install -U xpk`).
- `python3` and `kubectl` installed.

## Usage Guide

To launch the demo, execute these scripts in sequential order from this directory:

1. **`./00-setup-environment.sh`**: Interactively configures your environment variables and generates `env.sh`.
2. **`./01-create-cluster.sh`**: Provisions the required Spot GPU cluster using `xpk`.
3. **`./02-provision-lustre.sh`**: Requests the creation of the Managed Lustre filesystem array. *(Note: This can take ~10 minutes to become fully active)*.
4. **`./03-apply-ray-cluster.sh`**: Deploys the persistent volumes and the KubeRay `RayCluster` specification to your cluster.
5. **`./04-submit-workload.sh`**: Establishes a connection to the KubeRay head node, builds the runtime environment, and dispatches the training script.

### Checkpoints and Long-term Storage

This execution runs exclusively on the high-speed Lustre volume mounted at `/lustre` to avoid the checkpoint write penalties associated with directly mounting a GCS bucket. When execution completes, you can copy the checkpoints residing in your Lustre volume (`/lustre/nemo_rl_qwen_72b_ds_cp/*`) out to a GCS bucket for long-term storage using robust networking tools available in Ray or GCP, before executing the teardown sequence.

### Teardown
When you are finished exploring, use the cleanup script to halt all compute limits and charges:
```bash
./99-cleanup.sh
```
This drops the cluster alongside your Lustre storage array.
