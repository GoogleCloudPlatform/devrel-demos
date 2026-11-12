# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Removed or older Kubernetes API versions and deprecated annotations.

REMOVED means the version is no longer served by Kubernetes 1.37. OLDER means a
newer version is the current one; the older one may or may not still be served.
Entries follow the Kubernetes deprecated API migration guide.
"""

# (apiVersion, kind or "*", severity, note)
API_VERSIONS = [
    ("extensions/v1beta1", "*", "REMOVED", "use apps/v1, networking.k8s.io/v1"),
    ("apps/v1beta1", "*", "REMOVED", "use apps/v1"),
    ("apps/v1beta2", "*", "REMOVED", "use apps/v1"),
    ("policy/v1beta1", "PodSecurityPolicy", "REMOVED", "PodSecurityPolicy was removed; use Pod Security Admission"),
    ("policy/v1beta1", "PodDisruptionBudget", "REMOVED", "use policy/v1"),
    ("batch/v1beta1", "CronJob", "REMOVED", "use batch/v1"),
    ("networking.k8s.io/v1beta1", "*", "REMOVED", "use networking.k8s.io/v1"),
    ("rbac.authorization.k8s.io/v1beta1", "*", "REMOVED", "use rbac.authorization.k8s.io/v1"),
    ("admissionregistration.k8s.io/v1beta1", "*", "OLDER", "use admissionregistration.k8s.io/v1"),
    ("apiextensions.k8s.io/v1beta1", "*", "REMOVED", "use apiextensions.k8s.io/v1"),
    ("storage.k8s.io/v1beta1", "*", "OLDER", "use storage.k8s.io/v1"),
    ("scheduling.k8s.io/v1beta1", "PriorityClass", "REMOVED", "use scheduling.k8s.io/v1"),
    ("autoscaling/v2beta1", "*", "REMOVED", "use autoscaling/v2"),
    ("autoscaling/v2beta2", "*", "REMOVED", "use autoscaling/v2"),
    ("discovery.k8s.io/v1beta1", "*", "REMOVED", "use discovery.k8s.io/v1"),
    ("node.k8s.io/v1beta1", "*", "REMOVED", "use node.k8s.io/v1"),
    ("events.k8s.io/v1beta1", "*", "REMOVED", "use events.k8s.io/v1"),
    ("certificates.k8s.io/v1beta1", "CertificateSigningRequest", "REMOVED", "use certificates.k8s.io/v1"),
    ("coordination.k8s.io/v1beta1", "Lease", "REMOVED", "use coordination.k8s.io/v1"),
    ("flowcontrol.apiserver.k8s.io/v1beta1", "*", "REMOVED", "use flowcontrol.apiserver.k8s.io/v1"),
    ("flowcontrol.apiserver.k8s.io/v1beta2", "*", "REMOVED", "use flowcontrol.apiserver.k8s.io/v1"),
    ("flowcontrol.apiserver.k8s.io/v1beta3", "*", "REMOVED", "use flowcontrol.apiserver.k8s.io/v1"),
    ("resource.k8s.io/v1alpha2", "*", "REMOVED", "classic DRA was removed; use resource.k8s.io/v1"),
    ("resource.k8s.io/v1alpha3", "*", "OLDER", "use resource.k8s.io/v1"),
    ("resource.k8s.io/v1beta1", "*", "OLDER", "use resource.k8s.io/v1"),
    ("resource.k8s.io/v1beta2", "*", "OLDER", "use resource.k8s.io/v1"),
    ("kubescheduler.config.k8s.io/v1beta2", "*", "REMOVED", "use kubescheduler.config.k8s.io/v1"),
    ("kubescheduler.config.k8s.io/v1beta3", "*", "REMOVED", "use kubescheduler.config.k8s.io/v1"),
    ("agents.x-k8s.io/v1alpha1", "*", "OLDER", "Agent Sandbox storage version is v1beta1"),
    ("extensions.agents.x-k8s.io/v1alpha1", "*", "OLDER", "Agent Sandbox storage version is v1beta1"),
]

# Annotation prefixes that were replaced by fields.
ANNOTATIONS = [
    ("seccomp.security.alpha.kubernetes.io/", "REMOVED", "use securityContext.seccompProfile"),
    ("container.seccomp.security.alpha.kubernetes.io/", "REMOVED", "use securityContext.seccompProfile"),
    ("container.apparmor.security.beta.kubernetes.io/", "OLDER", "use securityContext.appArmorProfile"),
    ("scheduler.alpha.kubernetes.io/critical-pod", "REMOVED", "use priorityClassName"),
]


def _walk_annotations(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "annotations" and isinstance(value, dict):
                yield from value.keys()
            else:
                yield from _walk_annotations(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_annotations(item)


def find_stale(docs):
    """Return a list of (severity, message) for every stale API or annotation in docs."""
    hits = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        api, kind = doc.get("apiVersion", ""), doc.get("kind", "")
        for version, k, severity, note in API_VERSIONS:
            if api == version and (k == "*" or k == kind):
                hits.append((severity, f"{kind} uses {api}: {note}"))
                break
        for key in _walk_annotations(doc):
            for prefix, severity, note in ANNOTATIONS:
                if key.startswith(prefix):
                    hits.append((severity, f"annotation {key}: {note}"))
    return hits
