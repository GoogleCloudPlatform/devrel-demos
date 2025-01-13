// Copyright 2025 Google LLC.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// / Package p contains a Pub/Sub Cloud Function.

package p

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"golang.org/x/oauth2/google"
)

// PubSubMessage is the payload of a Pub/Sub event. Please refer to the docs for
// additional information regarding Pub/Sub events.
type PubSubMessage struct {
	Data []byte `json:"data"`
}

// apiURL is the base URL for the AlloyDB Admin API.
var apiURL string = "https://alloydb.googleapis.com/v1beta"

// Labels represents the labels associated with an AlloyDB resource.
type Labels struct {
	Cluster_id         string `json:"cluster_id"`
	Instance_id        string `json:"instance_id"`
	Location           string `json:"location"`
	Project_id         string `json:"project_id"`
	Resource_container string `json:"resource_container"`
}

// Resource represents an AlloyDB resource involved in an incident.
type Resource struct {
	Policy_name string `json:"policy_name"`
	Labels      Labels `json:"labels"`
	Type        string `json:"type"`
}

// Incident represents an incident triggering a scaling operation.
type Incident struct {
	Resource    Resource `json:"resource"`
	Policy_name string   `json:"policy_name"`
}

// Alert represents an alert containing incident details.
type Alert struct {
	Incident Incident `json:"incident"`
}

// MachineConfig represents the machine configuration of an AlloyDB instance.
type MachineConfig struct {
	CpuCount int `json:"cpuCount"`
}

// Instance represents an AlloyDB instance.
type Instance struct {
	Name          string        `json:"name"`
	DisplayName   string        `json:"displayName"`
	Uid           string        `json:"uid"`
	CreateTime    string        `json:"createTime"`
	UpdateTime    string        `json:"updateTime"`
	DeleteTime    string        `json:"deleteTime"`
	State         string        `json:"state"`
	InstanceType  string        `json:"instanceType"`
	MachineConfig MachineConfig `json:"machineConfig"`
	Description   string        `json:"description"`
	IpAddress     string        `json:"ipAddress"`
	Reconciling   bool          `json:"reconciling"`
	Etag          string        `json:"etag"`
}

// Instance_patch represents the fields to be patched in an Instance update.
type Instance_patch struct {
	InstanceType  string        `json:"instanceType"`
	MachineConfig MachineConfig `json:"machineConfig"`
}

// scaleUpInstance scales up the specified AlloyDB instance by doubling its CPU count.
func scaleUpInstance(ctx context.Context, project, location, cluster, instance string) error {
	// Scale Up an instance
	fmt.Println("Starting scaling up")

	// Create a new authenticated HTTP client using the application default credentials.
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		log.Fatal(err)
	}

	// Construct the URL to fetch the instance details
	instancesURL := apiURL + "/" + "projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances/" + instance
	fmt.Println(instancesURL)
	instancesReq, err := http.NewRequest("GET", instancesURL, nil)
	if err != nil {
		log.Fatal(err)
	}
	resp, err := client.Do(instancesReq)
	if err != nil {

		log.Fatal(err)
	}
	fmt.Println(resp.Status)

	instanceBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal(err)
	}

	var instance_json Instance
	err = json.Unmarshal(instanceBody, &instance_json)
	if err != nil {
		log.Println(err)
	}

	fmt.Println(instance_json.MachineConfig.CpuCount)

	// Double CPU count if it's less than 64
	if instance_json.MachineConfig.CpuCount < 64 {
		var instance_patch Instance_patch
		instance_patch.MachineConfig.CpuCount = instance_json.MachineConfig.CpuCount * 2
		instance_patch.InstanceType = instance_json.InstanceType

		fmt.Println(instance_patch.MachineConfig.CpuCount)
		instance_payload, err := json.Marshal(instance_patch)
		if err != nil {
			log.Fatal(err)
		}

		fmt.Println(instance_patch)
		fmt.Println(string(instance_payload))
		// Construct the URL for the PATCH request, including update mask.
		instancesURL = apiURL + "/" + "projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances/" + instance + "?updateMask=machineConfig.cpuCount"
		fmt.Println(instancesURL)
		// Create PATCH request to update the instance.
		instancesReq, err = http.NewRequest("PATCH", instancesURL, bytes.NewBuffer(instance_payload))
		if err != nil {
			log.Fatal(err)
		}

		resp, err = client.Do(instancesReq)
		if err != nil {

			log.Fatal(err)
		}
		fmt.Println(resp)
	}

	return nil
}

// scaleDownInstance scales down the specified AlloyDB instance by halving its CPU count.
func scaleDownInstance(ctx context.Context, project, location, cluster, instance string) error {
	// Scale down the instance
	fmt.Println("Starting scaling down")
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		log.Fatal(err)
	}
	instancesURL := apiURL + "/" + "projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances/" + instance
	fmt.Println(instancesURL)
	instancesReq, err := http.NewRequest("GET", instancesURL, nil)
	if err != nil {
		log.Fatal(err)
	}
	resp, err := client.Do(instancesReq)
	if err != nil {

		log.Fatal(err)
	}
	fmt.Println(resp.Status)

	instanceBody, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatal(err)
	}

	var instance_json Instance
	err = json.Unmarshal(instanceBody, &instance_json)
	if err != nil {
		log.Println(err)
	}

	fmt.Println(instance_json.MachineConfig.CpuCount)

	// Halve the CPU count if it's greater than 2.
	if instance_json.MachineConfig.CpuCount > 2 {
		var instance_patch Instance_patch
		instance_patch.MachineConfig.CpuCount = instance_json.MachineConfig.CpuCount / 2
		instance_patch.InstanceType = instance_json.InstanceType

		fmt.Println(instance_patch.MachineConfig.CpuCount)
		instance_payload, err := json.Marshal(instance_patch)
		if err != nil {
			log.Fatal(err)
		}

		fmt.Println(instance_patch)
		fmt.Println(string(instance_payload))

		instancesURL = apiURL + "/" + "projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances/" + instance + "?updateMask=machineConfig.cpuCount"
		fmt.Println(instancesURL)
		instancesReq, err = http.NewRequest("PATCH", instancesURL, bytes.NewBuffer(instance_payload))
		if err != nil {
			log.Fatal(err)
		}

		resp, err = client.Do(instancesReq)
		if err != nil {

			log.Fatal(err)
		}
		fmt.Println(resp)
	}
	return nil
}

// ScaleAlloyDBInstance scales an AlloyDB instance based on the received Pub/Sub message.
func ScaleAlloyDBInstance(ctx context.Context, m PubSubMessage) error {
	var alert Alert
	err := json.Unmarshal(m.Data, &alert)
	if err != nil {
		log.Println(err)
	}

	fmt.Println(alert.Incident.Policy_name)
	project := alert.Incident.Resource.Labels.Project_id
	location := alert.Incident.Resource.Labels.Location
	cluster := alert.Incident.Resource.Labels.Cluster_id
	instance := alert.Incident.Resource.Labels.Instance_id
	instanceoperation := alert.Incident.Policy_name

	if instanceoperation == "alloydb-scale-up" {
		//
		err := scaleUpInstance(ctx, project, location, cluster, instance)
		if err != nil {
			log.Println(err)
		}
	} else if instanceoperation == "alloydb-scale-down" {
		//
		err := scaleDownInstance(ctx, project, location, cluster, instance)
		if err != nil {
			log.Println(err)
		}
	}

	fmt.Println("Done ScaleAlloyDBInstance")

	return nil
}
