// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

// Snapshot is what census records for one cluster. The same shape is used for
// the hand-written 2020 baseline in ep01-revisited/baseline/.
type Snapshot struct {
	Context        string              `json:"context"`
	CollectedAt    string              `json:"collectedAt"`
	Source         string              `json:"source,omitempty"`
	ServerVersion  string              `json:"serverVersion"`
	APIGroups      map[string][]string `json:"apiGroups"`
	Capabilities   map[string]bool     `json:"capabilities"`
	RuntimeClasses []string            `json:"runtimeClasses"`
	FeatureGates   map[string]Gate     `json:"featureGates"`
	Nodes          []NodeInfo          `json:"nodes,omitempty"`
	Errors         []string            `json:"errors,omitempty"`
}

// Gate is a feature gate as reported by kubernetes_feature_enabled.
type Gate struct {
	Enabled bool   `json:"enabled"`
	Stage   string `json:"stage,omitempty"`
}

// NodeInfo is a short summary of one node.
type NodeInfo struct {
	Name             string   `json:"name"`
	Pool             string   `json:"pool,omitempty"`
	KubeletVersion   string   `json:"kubeletVersion,omitempty"`
	DeclaredFeatures []string `json:"declaredFeatures,omitempty"`
}

// capability is a named check: is this resource served at this group/version?
type capability struct {
	ID, Label, GroupVersion, Resource string
}

// Pod certificates and ClusterTrustBundle are certificates.k8s.io/v1 from 1.37. Kueue's storage
// version is kueue.x-k8s.io/v1beta2 from Kueue v0.16 (v1beta1 is deprecated).
var capabilities = []capability{
	{"dra.v1", "DRA (resource.k8s.io/v1)", "resource.k8s.io/v1", "deviceclasses"},
	{"workload.v1beta1", "Workload API (scheduling.k8s.io/v1beta1)", "scheduling.k8s.io/v1beta1", "workloads"},
	{"podgroup.v1beta1", "PodGroup API (scheduling.k8s.io/v1beta1)", "scheduling.k8s.io/v1beta1", "podgroups"},
	{"vap.v1", "ValidatingAdmissionPolicy (v1)", "admissionregistration.k8s.io/v1", "validatingadmissionpolicies"},
	{"map.v1", "MutatingAdmissionPolicy (v1)", "admissionregistration.k8s.io/v1", "mutatingadmissionpolicies"},
	{"podcertificates.v1", "Pod certificates (certificates.k8s.io/v1)", "certificates.k8s.io/v1", "podcertificaterequests"},
	{"clustertrustbundles.v1", "ClusterTrustBundle (certificates.k8s.io/v1)", "certificates.k8s.io/v1", "clustertrustbundles"},
	{"agentsandbox", "Agent Sandbox (agents.x-k8s.io/v1beta1)", "agents.x-k8s.io/v1beta1", "sandboxes"},
	{"agentsandbox.claims", "Agent Sandbox claims (extensions.agents.x-k8s.io/v1beta1)", "extensions.agents.x-k8s.io/v1beta1", "sandboxclaims"},
	{"podsnapshots", "Pod Snapshots (podsnapshot.gke.io/v1)", "podsnapshot.gke.io/v1", "podsnapshots"},
	{"nfd.nodefeatures", "Node Feature Discovery (nfd.k8s-sigs.io/v1alpha1)", "nfd.k8s-sigs.io/v1alpha1", "nodefeatures"},
	{"kueue", "Kueue (kueue.x-k8s.io/v1beta2)", "kueue.x-k8s.io/v1beta2", "clusterqueues"},
}

// Feature gates shown in the Markdown table; the JSON keeps every gate.
var tableGates = []string{"GenericWorkload", "TopologyAwareWorkloadScheduling", "DRADerivedAttributes",
	"MemoryQoS", "PodLevelResources", "PodLevelResourceManagers", "InPlacePodVerticalScalingExclusiveCPUs",
	"SchedulerAsyncAPICalls", "OpportunisticBatching"}

// Node labels that name a node's pool. GKE sets the first; the second is a
// common convention on self-managed clusters.
var poolLabels = []string{"cloud.google.com/gke-nodepool", "node.kubernetes.io/pool"}

func runCensus(args []string) int {
	var outDir string
	c, err := parseCommon("census", args, func(fs *flag.FlagSet) {
		fs.StringVar(&outDir, "out-dir", "", "write census-<context>.json files here")
	})
	if err != nil {
		return 2
	}
	var snaps []*Snapshot
	for _, ctxName := range c.contexts {
		s := collect(c.kubeconfig, ctxName)
		snaps = append(snaps, s)
		if outDir != "" {
			if err := writeJSON(filepath.Join(outDir, "census-"+safeName(s.Context)+".json"), s); err != nil {
				fmt.Fprintln(os.Stderr, err)
				return 1
			}
		}
	}
	if c.format == "json" {
		return printJSON(snaps)
	}
	fmt.Print(renderCensus(snaps))
	return 0
}

func collect(kubeconfig, ctxName string) *Snapshot {
	s := &Snapshot{
		Context:      ctxName,
		CollectedAt:  time.Now().UTC().Format(time.RFC3339),
		APIGroups:    map[string][]string{},
		Capabilities: map[string]bool{},
		FeatureGates: map[string]Gate{},
	}
	cs, _, name, err := clientFor(kubeconfig, ctxName)
	s.Context = name
	if err != nil {
		s.Errors = append(s.Errors, "client: "+err.Error())
		return s
	}
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	if v, err := cs.Discovery().ServerVersion(); err == nil {
		s.ServerVersion = v.GitVersion
	} else {
		s.Errors = append(s.Errors, "version: "+err.Error())
	}
	if groups, err := cs.Discovery().ServerGroups(); err == nil {
		for _, g := range groups.Groups {
			name := g.Name
			if name == "" {
				name = "core"
			}
			for _, v := range g.Versions {
				s.APIGroups[name] = append(s.APIGroups[name], v.Version)
			}
		}
	} else {
		s.Errors = append(s.Errors, "groups: "+err.Error())
	}
	for _, capa := range capabilities {
		s.Capabilities[capa.ID] = served(cs, capa.GroupVersion, capa.Resource)
	}
	if rcs, err := cs.NodeV1().RuntimeClasses().List(ctx, metav1.ListOptions{}); err == nil {
		for _, rc := range rcs.Items {
			s.RuntimeClasses = append(s.RuntimeClasses, rc.Name)
		}
		sort.Strings(s.RuntimeClasses)
	} else {
		s.Errors = append(s.Errors, "runtimeclasses: "+err.Error())
	}
	if raw, err := cs.CoreV1().RESTClient().Get().AbsPath("/metrics").DoRaw(ctx); err == nil {
		s.FeatureGates = parseFeatureGates(string(raw))
	} else {
		s.Errors = append(s.Errors, "apiserver metrics: "+err.Error())
	}
	s.Nodes, err = nodeInfo(ctx, cs)
	if err != nil {
		s.Errors = append(s.Errors, "nodes: "+err.Error())
	}
	return s
}

func served(cs *kubernetes.Clientset, gv, resource string) bool {
	list, err := cs.Discovery().ServerResourcesForGroupVersion(gv)
	if err != nil || list == nil {
		return false
	}
	for _, r := range list.APIResources {
		if r.Name == resource {
			return true
		}
	}
	return false
}

func poolOf(labels map[string]string) string {
	for _, k := range poolLabels {
		if v, ok := labels[k]; ok {
			return v
		}
	}
	if _, ok := labels["node-role.kubernetes.io/control-plane"]; ok {
		return "control-plane"
	}
	return "default"
}

func nodeInfo(ctx context.Context, cs *kubernetes.Clientset) ([]NodeInfo, error) {
	nodes, err := cs.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return nil, err
	}
	var out []NodeInfo
	for _, n := range nodes.Items {
		ni := NodeInfo{Name: n.Name, Pool: poolOf(n.Labels), KubeletVersion: n.Status.NodeInfo.KubeletVersion}
		// declaredFeatures is read from raw JSON so this works whatever its Go type is.
		if raw, err := cs.CoreV1().RESTClient().Get().Resource("nodes").Name(n.Name).DoRaw(ctx); err == nil {
			ni.DeclaredFeatures = declaredFeatures(raw)
		}
		out = append(out, ni)
	}
	return out, nil
}

func declaredFeatures(raw []byte) []string {
	var obj struct {
		Status map[string]json.RawMessage `json:"status"`
	}
	if json.Unmarshal(raw, &obj) != nil {
		return nil
	}
	field, ok := obj.Status["declaredFeatures"]
	if !ok {
		return nil
	}
	var names []string
	if json.Unmarshal(field, &names) == nil {
		return names
	}
	var objs []map[string]any
	if json.Unmarshal(field, &objs) == nil {
		for _, o := range objs {
			if n, ok := o["name"].(string); ok {
				names = append(names, n)
			}
		}
	}
	return names
}

var gateLine = regexp.MustCompile(`^kubernetes_feature_enabled\{([^}]*)\}\s+([0-9.eE+-]+)`)
var labelPair = regexp.MustCompile(`(\w+)="([^"]*)"`)

// parseFeatureGates reads kubernetes_feature_enabled samples from Prometheus text.
func parseFeatureGates(metrics string) map[string]Gate {
	gates := map[string]Gate{}
	for _, line := range strings.Split(metrics, "\n") {
		m := gateLine.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		labels := map[string]string{}
		for _, p := range labelPair.FindAllStringSubmatch(m[1], -1) {
			labels[p[1]] = p[2]
		}
		v, _ := strconv.ParseFloat(m[2], 64)
		if name := labels["name"]; name != "" {
			gates[name] = Gate{Enabled: v == 1, Stage: labels["stage"]}
		}
	}
	return gates
}

func safeName(s string) string {
	if s == "" {
		return "current"
	}
	return regexp.MustCompile(`[^A-Za-z0-9._-]+`).ReplaceAllString(s, "-")
}

func writeJSON(path string, v any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}

func printJSON(v any) int {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}
	fmt.Println(string(data))
	return 0
}
