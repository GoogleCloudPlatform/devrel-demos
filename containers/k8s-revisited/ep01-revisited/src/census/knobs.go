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
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"
)

// Kubelet configuration fields read from /configz. Dotted paths go into nested objects.
var knobFields = []string{
	"cpuManagerPolicy", "cpuManagerPolicyOptions", "reservedSystemCPUs", "cpuCFSQuota", "cpuCFSQuotaPeriod",
	"memoryManagerPolicy", "topologyManagerPolicy", "topologyManagerScope", "topologyManagerPolicyOptions",
	"failSwapOn", "memorySwap.swapBehavior", "maxPods", "podPidsLimit", "serializeImagePulls",
	"maxParallelImagePulls", "imageGCHighThresholdPercent", "imageGCLowThresholdPercent", "imageMaximumGCAge",
	"singleProcessOOMKill", "containerLogMaxSize", "featureGates",
}

// Kubelet feature gates read from the kubelet's /metrics.
var kubeletGates = []string{"MemoryQoS", "PodLevelResources", "PodLevelResourceManagers", "InPlacePodVerticalScaling",
	"InPlacePodVerticalScalingExclusiveCPUs", "KubeletPSI", "UserNamespacesSupport", "ImageVolume", "NodeSwap",
	"EventedPLEG", "NodeDeclaredFeatures"}

// PoolKnobs is the effective kubelet configuration of one node, standing in for its pool.
type PoolKnobs struct {
	Context string          `json:"context"`
	Pool    string          `json:"pool"`
	Node    string          `json:"node"`
	Config  map[string]any  `json:"kubeletConfig"`
	Gates   map[string]Gate `json:"kubeletFeatureGates"`
	Error   string          `json:"error,omitempty"`
}

func runKnobs(args []string) int {
	c, err := parseCommon("census knobs", args, nil)
	if err != nil {
		return 2
	}
	var all []PoolKnobs
	for _, ctxName := range c.contexts {
		cs, _, name, err := clientFor(c.kubeconfig, ctxName)
		if err != nil {
			all = append(all, PoolKnobs{Context: name, Error: err.Error()})
			continue
		}
		all = append(all, collectKnobs(cs, name)...)
	}
	if c.format == "json" {
		return printJSON(all)
	}
	fmt.Print(renderKnobs(all))
	return 0
}

func collectKnobs(cs *kubernetes.Clientset, ctxName string) []PoolKnobs {
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()
	nodes, err := cs.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return []PoolKnobs{{Context: ctxName, Error: err.Error()}}
	}
	seen := map[string]bool{}
	var out []PoolKnobs
	for _, n := range nodes.Items {
		pool := poolOf(n.Labels)
		if seen[pool] {
			continue
		}
		seen[pool] = true
		pk := PoolKnobs{Context: ctxName, Pool: pool, Node: n.Name, Config: map[string]any{}, Gates: map[string]Gate{}}
		proxy := cs.CoreV1().RESTClient().Get().Resource("nodes").Name(n.Name).SubResource("proxy")
		if raw, err := proxy.Suffix("configz").DoRaw(ctx); err == nil {
			var cz struct {
				KubeletConfig map[string]any `json:"kubeletconfig"`
			}
			if err := json.Unmarshal(raw, &cz); err == nil {
				for _, f := range knobFields {
					if v, ok := lookup(cz.KubeletConfig, f); ok {
						pk.Config[f] = v
					}
				}
			}
		} else {
			pk.Error = "configz: " + err.Error()
		}
		proxy = cs.CoreV1().RESTClient().Get().Resource("nodes").Name(n.Name).SubResource("proxy")
		if raw, err := proxy.Suffix("metrics").DoRaw(ctx); err == nil {
			gates := parseFeatureGates(string(raw))
			for _, g := range kubeletGates {
				if v, ok := gates[g]; ok {
					pk.Gates[g] = v
				}
			}
		} else if pk.Error == "" {
			pk.Error = "metrics: " + err.Error()
		}
		out = append(out, pk)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Pool < out[j].Pool })
	return out
}

func lookup(m map[string]any, path string) (any, bool) {
	var cur any = m
	for _, part := range strings.Split(path, ".") {
		obj, ok := cur.(map[string]any)
		if !ok {
			return nil, false
		}
		cur, ok = obj[part]
		if !ok {
			return nil, false
		}
	}
	return cur, true
}

func cell(v any, ok bool) string {
	if !ok {
		return "unset"
	}
	switch t := v.(type) {
	case string:
		return t
	default:
		data, _ := json.Marshal(t)
		return string(data)
	}
}

func renderKnobs(all []PoolKnobs) string {
	var b strings.Builder
	header := []string{"Knob"}
	for _, pk := range all {
		header = append(header, pk.Context+"/"+pk.Pool)
	}
	b.WriteString(row(header...))
	sep := make([]string, len(header))
	for i := range sep {
		sep[i] = "---"
	}
	b.WriteString(row(sep...))
	for _, f := range knobFields {
		r := []string{f}
		for _, pk := range all {
			v, ok := pk.Config[f]
			r = append(r, cell(v, ok))
		}
		b.WriteString(row(r...))
	}
	for _, g := range kubeletGates {
		r := []string{"feature gate " + g + " (kubelet)"}
		for _, pk := range all {
			v, ok := pk.Gates[g]
			r = append(r, gateCell(v, ok))
		}
		b.WriteString(row(r...))
	}
	for _, pk := range all {
		if pk.Error != "" {
			fmt.Fprintf(os.Stderr, "%s/%s: %s\n", pk.Context, pk.Pool, pk.Error)
		}
	}
	return b.String()
}
