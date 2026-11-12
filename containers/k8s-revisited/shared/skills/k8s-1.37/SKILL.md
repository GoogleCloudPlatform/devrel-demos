---
name: kubernetes-1-37-manifests
description: Use when writing or reviewing Kubernetes manifests that must work on Kubernetes 1.37, including on GKE. Lists the current API versions, features that graduated since 2020, patterns that older docs still show, and GKE notes from hands-on runs.
---

# Writing manifests for Kubernetes 1.37

> Checked on 2026-11-10 against the Kubernetes documentation, the API groups served by GKE 1.37 clusters, and the Agent Sandbox project docs. The GKE notes come from runs on GKE 1.37 and 1.35 in November 2026.

## Use these API versions

| Kind | apiVersion |
|---|---|
| Deployment, StatefulSet, DaemonSet, ReplicaSet | `apps/v1` |
| Job, CronJob | `batch/v1` |
| Ingress, IngressClass, NetworkPolicy | `networking.k8s.io/v1` |
| PodDisruptionBudget | `policy/v1` |
| HorizontalPodAutoscaler | `autoscaling/v2` |
| PriorityClass | `scheduling.k8s.io/v1` |
| Workload, PodGroup | `scheduling.k8s.io/v1beta1`, only where the `GenericWorkload` feature gate is on (it's off by default) |
| DeviceClass, ResourceClaim, ResourceClaimTemplate, ResourceSlice | `resource.k8s.io/v1` |
| ValidatingAdmissionPolicy, MutatingAdmissionPolicy and their bindings | `admissionregistration.k8s.io/v1` |
| FlowSchema, PriorityLevelConfiguration | `flowcontrol.apiserver.k8s.io/v1` |
| RuntimeClass | `node.k8s.io/v1` |
| KubeSchedulerConfiguration | `kubescheduler.config.k8s.io/v1` |
| Sandbox (Agent Sandbox CRD) | `agents.x-k8s.io/v1beta1` |
| SandboxTemplate, SandboxWarmPool, SandboxClaim (Agent Sandbox CRDs) | `extensions.agents.x-k8s.io/v1beta1` |

PodSecurityPolicy no longer exists. Use Pod Security Admission labels on the namespace.

## Features to reach for

- **Native sidecars:** an init container with `restartPolicy: Always` starts before the app containers and keeps running.
- **In-place resize:** set `resizePolicy` per resource on the container, then change resources through the `resize` subresource (`kubectl patch pod NAME --subresource resize ...`).
- **Image volumes:** `volumes[].image.reference` mounts an OCI image or artifact read-only. Use it for model weights instead of an init container download.
- **User namespaces:** `spec.hostUsers: false` maps container root to an unprivileged user on the node.
- **Seccomp:** `securityContext.seccompProfile.type: RuntimeDefault`, not the old annotations.
- **Scheduling gates:** `spec.schedulingGates` holds a Pod back until a controller removes the gate.
- **Topology spread per rollout:** `topologySpreadConstraints[].matchLabelKeys: [pod-template-hash]`.
- **DRA:** a ResourceClaimTemplate lists requests under `spec.spec.devices.requests[]`; each request sets exactly one of `exactly` (a single choice) or `firstAvailable` (an ordered fallback list). The Pod references the template from `spec.resourceClaims[].resourceClaimTemplateName`, and the container from `resources.claims[].name`.

## Patterns older docs still show (avoid)

- `extensions/v1beta1`, `apps/v1beta1`, `apps/v1beta2`, `policy/v1beta1`, `batch/v1beta1`, `networking.k8s.io/v1beta1`
- `seccomp.security.alpha.kubernetes.io/*` and `container.apparmor.security.beta.kubernetes.io/*` annotations
- A sidecar as a second regular container with no startup ordering
- `resource.k8s.io/v1alpha2` (classic DRA, removed)
- `kubescheduler.config.k8s.io/v1beta2` and `v1beta3`

## GKE notes

- **Swap** is a GKE Standard node pool setting (`linuxConfig.swapConfig` in the node system config). Only Burstable Pods use it.
- **Kubelet settings** such as the CPU Manager policy are set per node pool in the node system config (`kubeletConfig`), not with a `KubeletConfiguration` object.
- **Autopilot** checks Pods at admission:
  - allowed volume types are `configMap`, `csi`, `downwardAPI`, `emptyDir`, `gcePersistentDisk`, `hostPath`, `nfs`, `persistentVolumeClaim`, `projected`, `secret` and `ephemeral` (so no image volumes);
  - the memory request has to stay within a range relative to the CPU request, and a resize that raises only CPU can be rejected for it;
  - the `nodes/proxy` permission can't be granted.
