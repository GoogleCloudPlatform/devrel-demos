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
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"cloud.google.com/go/pubsub" // Added for alert publishing
	"golang.org/x/oauth2/google"
)

// PubSubMessage is the payload of a Pub/Sub event. Please refer to the docs for
// additional information regarding Pub/Sub events.
type PubSubMessage struct {
	Data []byte `json:"data"`
}

// Parameters holds parameters for the ManageAlloyDBInstances function.
type Parameters struct {
	Project   string `json:"project"`
	Location  string `json:"location"`
	Operation string `json:"operation"`
	Cluster   string `json:"cluster"`
	Instance  string `json:"instance"`
	Retention int    `json:"retention"`
}

// --- STRUCTS FOR NEW CHECK FUNCTION ---

// InstanceCheckRule defines a specific check and action.
type InstanceCheckRule struct {
	TargetFlagName   string `json:"targetFlagName"`   // e.g., "max_connections"
	CorrectFlagValue string `json:"correctFlagValue"` // e.g., "1000" (optional, if empty for max_connections, it's calculated)
	AlertTopic       string `json:"alertTopic"`       // Pub/Sub topic to send alerts to (optional)
}

// CheckInstanceParams holds parameters for the CheckAlloyDBInstances function.
type CheckInstanceParams struct {
	Project  string              `json:"project"`
	Location string              `json:"location"` // e.g., "us-central1" or "ALL"
	Cluster  string              `json:"cluster"`  // e.g., "my-cluster" or "ALL"
	Instance string              `json:"instance"` // e.g., "my-instance" or "ALL"
	Rules    []InstanceCheckRule `json:"rules"`
	Debug    bool                `json:"debug,omitempty"`
}

// AlertMessage is the payload published to the Pub/Sub alert topic.
type AlertMessage struct {
	InstanceName              string            `json:"instanceName"`
	DisplayName               string            `json:"displayName"`
	CheckRule                 InstanceCheckRule `json:"checkRule"`
	Message                   string            `json:"message"`
	CorrectiveActionAttempted bool              `json:"correctiveActionAttempted"`
	CorrectionError           string            `json:"correctionError,omitempty"`
}

// --- END NEW CHECK STRUCTS ---

var apiURL string = "https://alloydb.googleapis.com/v1beta"

// List of AlloyDB instances from API response
type Instances struct {
	Instances []Instance `json:"instances"`
}

// MachineConfig represents the machine configuration of an Instance.
type MachineConfig struct {
	CpuCount int `json:"cpuCount"`
}

// A single instance from the list
type Instance struct {
	Name          string            `json:"name"`
	DisplayName   string            `json:"displayName"`
	Uid           string            `json:"uid"`
	CreateTime    string            `json:"createTime"`
	UpdateTime    string            `json:"updateTime"`
	State         string            `json:"state"`
	InstanceType  string            `json:"instanceType"`
	IpAddress     string            `json:"ipAddress"`
	MachineConfig MachineConfig     `json:"machineConfig"`
	DatabaseFlags map[string]string `json:"databaseFlags"`
}

// List of available locations
type Locations struct {
	Locations []Location `json:"locations"`
}

// Location is a single location
type Location struct {
	LocationId string `json:"locationId"`
}

// --- STRUCTS FOR LRO (LONG RUNNING OPERATION) ---

// Operation represents a long-running operation.
type Operation struct {
	Name  string  `json:"name"`
	Done  bool    `json:"done"`
	Error *Status `json:"error,omitempty"`
}

// Status represents an error status.
type Status struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// --- END LRO STRUCTS ---

type ClusterInstances struct {
	ClusterID string
	Primary   *Instance
	ReadPools []*Instance
}

// getClusterNameFromResourceName extracts the cluster ID from a full instance resource name.
// Format: projects/{project}/locations/{location}/clusters/{cluster}/instances/{instance}
func getClusterNameFromResourceName(resourceName string) string {
	parts := strings.Split(resourceName, "/")
	if len(parts) >= 6 {
		return parts[5]
	}
	return "unknown"
}

// getInstance fetches the current details for a single instance.
func getInstance(ctx context.Context, instanceName string) (*Instance, error) {
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, fmt.Errorf("failed to create client: %v", err)
	}
	instanceURL := apiURL + "/" + instanceName
	resp, err := client.Get(instanceURL)
	if err != nil {
		return nil, fmt.Errorf("failed to get instance %s: %v", instanceName, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to get instance %s, status: %s, body: %s", instanceName, resp.Status, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read instance response body: %v", err)
	}
	var instance Instance
	if err := json.Unmarshal(body, &instance); err != nil {
		return nil, fmt.Errorf("failed to unmarshal instance: %v", err)
	}
	return &instance, nil
}

// waitForInstanceState polls an instance until it reaches a desired state or times out.
func waitForInstanceState(ctx context.Context, instanceName, desiredState string, timeout time.Duration) error {
	fmt.Printf("Waiting for instance %s to reach state %s...\n", instanceName, desiredState)
	timeoutChan := time.After(timeout)
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeoutChan:
			return fmt.Errorf("timeout reached while waiting for instance %s to become %s", instanceName, desiredState)
		case <-ticker.C:
			instanceDetails, err := getInstance(ctx, instanceName)
			if err != nil {
				log.Printf("could not get status for %s, retrying: %v", instanceName, err)
				continue
			}
			fmt.Printf("Instance %s current state: %s\n", instanceDetails.Name, instanceDetails.State)
			if instanceDetails.State == desiredState {
				fmt.Printf("Instance %s has reached desired state %s.\n", instanceName, desiredState)
				return nil
			}
		}
	}
}

// listInstances retrieves a list of instances based on project, location, and cluster
func listInstances(ctx context.Context, project, location, cluster string) ([]Instance, error) {
	lstInst := []Instance{}
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, fmt.Errorf("failed to create default client: %v", err)
	}
	var instancesURL string
	if location == "ALL" {
		if cluster == "ALL" {
			instancesURL = fmt.Sprintf("%s/projects/%s/locations/-/clusters/-/instances", apiURL, project)
		} else {
			locationsURL := fmt.Sprintf("%s/projects/%s/locations", apiURL, project)
			resp, err := client.Get(locationsURL)
			if err != nil {
				return nil, fmt.Errorf("failed to get all locations for project %s: %v", project, err)
			}
			defer resp.Body.Close()
			locationsListBody, err := io.ReadAll(resp.Body)
			if err != nil {
				return nil, fmt.Errorf("failed to read all locations response: %v", err)
			}
			locations := Locations{}
			err = json.Unmarshal(locationsListBody, &locations)
			if err != nil {
				return nil, fmt.Errorf("failed to unmarshal all locations: %v", err)
			}
			for _, loc := range locations.Locations {
				instancesURL = fmt.Sprintf("%s/projects/%s/locations/%s/clusters/%s/instances", apiURL, project, loc.LocationId, cluster)
				resp, err := client.Get(instancesURL)
				if err != nil {
					log.Printf("could not get instances for cluster %s in location %s: %v", cluster, loc.LocationId, err)
					continue
				}
				instancesListBody, err := io.ReadAll(resp.Body)
				if err != nil {
					log.Printf("could not read instance body for cluster %s in location %s: %v", cluster, loc.LocationId, err)
					resp.Body.Close()
					continue
				}
				resp.Body.Close()
				instances := Instances{}
				if err = json.Unmarshal(instancesListBody, &instances); err == nil && len(instances.Instances) > 0 {
					lstInst = append(lstInst, instances.Instances...)
				}
			}
			return lstInst, nil
		}
	} else {
		if cluster == "ALL" {
			instancesURL = apiURL + "/projects/" + project + "/locations/" + location + "/clusters/-/instances"
		} else {
			instancesURL = apiURL + "/projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances"
		}
	}
	resp, err := client.Get(instancesURL)
	if err != nil {
		return nil, fmt.Errorf("failed to get all instances: %v", err)
	}
	defer resp.Body.Close()
	instancesListBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read all instances response: %v", err)
	}
	instances := Instances{}
	if err = json.Unmarshal(instancesListBody, &instances); err != nil {
		return nil, fmt.Errorf("failed to unmarshal all instances: %v", err)
	}
	lstInst = append(lstInst, instances.Instances...)
	return lstInst, nil
}

// deleteInstance sends a API request to delete an instance
func deleteInstance(ctx context.Context, instance string) error {
	fmt.Println("Starting delete:", instance)
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to create default client: %v", err)
	}
	instancesURL := apiURL + "/" + instance
	instancesReq, err := http.NewRequest("DELETE", instancesURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create DELETE request: %v", err)
	}
	resp, err := client.Do(instancesReq)
	if err != nil {
		return fmt.Errorf("failed to proceed the DELETE request: %v", err)
	}
	defer resp.Body.Close()
	fmt.Println("Delete Response", resp.Status)
	return nil
}

// failoverInstance post a request to failover an instance.
func failoverInstance(ctx context.Context, instance string) error {
	fmt.Println("Starting failover for ", instance)
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to create client for failover: %v", err)
	}
	instancesURL := apiURL + "/" + instance + ":failover"
	instancesReq, err := http.NewRequest("POST", instancesURL, nil)
	if err != nil {
		return fmt.Errorf("failed to create request for failover: %v", err)
	}
	resp, err := client.Do(instancesReq)
	if err != nil {
		return fmt.Errorf("failed to post the failover request: %v", err)
	}
	defer resp.Body.Close()
	fmt.Println("Failover Response ", resp.Status)
	return nil
}

// stopInstance sends a request to stop an instance by updating its activation policy.
func stopInstance(ctx context.Context, instance string) error {
	fmt.Println("Initiating stop for instance:", instance)
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to create client to stop instance: %v", err)
	}

	instanceURL := apiURL + "/" + instance + "?updateMask=activation_policy"
	payload := `{"activation_policy": "NEVER"}`
	req, err := http.NewRequest("PATCH", instanceURL, strings.NewReader(payload))
	if err != nil {
		return fmt.Errorf("failed to create stop request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute stop request: %v", err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	fmt.Println("Stop Response Status:", resp.Status)
	fmt.Println("Stop Response Body:", string(body))
	return nil
}

// startInstance sends a request to start an instance by updating its activation policy.
func startInstance(ctx context.Context, instance string) error {
	fmt.Println("Initiating start for instance:", instance)
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to create client to start instance: %v", err)
	}

	instanceURL := apiURL + "/" + instance + "?updateMask=activation_policy"
	payload := `{"activation_policy": "ALWAYS"}`
	req, err := http.NewRequest("PATCH", instanceURL, strings.NewReader(payload))
	if err != nil {
		return fmt.Errorf("failed to create start request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute start request: %v", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	fmt.Println("Start Response Status:", resp.Status)
	fmt.Println("Start Response Body:", string(body))
	return nil
}

// ManageAlloyDBInstances is the main entry point for the Cloud Function.
func ManageAlloyDBInstances(ctx context.Context, m PubSubMessage) error {
	var par Parameters
	if err := json.Unmarshal(m.Data, &par); err != nil {
		log.Printf("Failed to unmarshal json: %v", err)
		return err
	}
	project := par.Project
	location := par.Location
	cluster := par.Cluster
	instanceoperation := par.Operation

	instances, err := listInstances(ctx, project, location, cluster)
	if err != nil {
		log.Printf("error listing instances: %v", err)
		return err
	}

	// Group instances by cluster for coordinated operations
	clustersMap := make(map[string]*ClusterInstances)
	for i := range instances {
		inst := &instances[i]
		cID := getClusterNameFromResourceName(inst.Name)
		if _, ok := clustersMap[cID]; !ok {
			clustersMap[cID] = &ClusterInstances{ClusterID: cID}
		}
		if inst.InstanceType == "PRIMARY" {
			clustersMap[cID].Primary = inst
		} else if inst.InstanceType == "READ_POOL" {
			clustersMap[cID].ReadPools = append(clustersMap[cID].ReadPools, inst)
		}
	}

	switch strings.ToUpper(instanceoperation) {
	case "LIST":
		fmt.Println("Listing instances")
		for _, instance := range instances {
			fmt.Println(instance.Name)
		}
	case "FAILOVER":
		for _, instance := range instances {
			fmt.Println("Failing over instance ", instance.Name)
			if err := failoverInstance(ctx, instance.Name); err != nil {
				log.Printf("failover error for instance %s: %v", instance.Name, err)
			}
		}
	case "DELETE":
		for _, instance := range instances {
			fmt.Println("Deleting instance ", instance.Name)
			if err := deleteInstance(ctx, instance.Name); err != nil {
				log.Printf("error deleting for instance %s: %v", instance.Name, err)
			}
		}
	case "STOP":
		fmt.Printf("Initiating STOP operation for %d clusters in parallel...\n", len(clustersMap))
		var wg sync.WaitGroup
		for _, cInsts := range clustersMap {
			wg.Add(1)
			go func(ci *ClusterInstances) {
				defer wg.Done()
				handleClusterStop(ctx, ci)
			}(cInsts)
		}
		wg.Wait()
	case "START":
		fmt.Printf("Initiating START operation for %d clusters in parallel...\n", len(clustersMap))
		var wg sync.WaitGroup
		for _, cInsts := range clustersMap {
			wg.Add(1)
			go func(ci *ClusterInstances) {
				defer wg.Done()
				handleClusterStart(ctx, ci)
			}(cInsts)
		}
		wg.Wait()
	default:
		log.Printf("unknown operation requested: %s", instanceoperation)
	}
	fmt.Println("Done ManageAlloyDBInstances")
	return nil
}

func handleClusterStart(ctx context.Context, cInsts *ClusterInstances) {
	log.Printf("[%s] Starting cluster...", cInsts.ClusterID)

	// 1. Start Primary first
	if cInsts.Primary != nil {
		log.Printf("[%s] Initiating START for primary: %s", cInsts.ClusterID, cInsts.Primary.Name)
		if err := startInstance(ctx, cInsts.Primary.Name); err != nil {
			log.Printf("[%s] ERROR starting primary %s: %v", cInsts.ClusterID, cInsts.Primary.Name, err)
			return // Cannot proceed with read pools if primary fails to start
		}
		// Wait for Primary to be READY before starting read pools
		if err := waitForInstanceState(ctx, cInsts.Primary.Name, "READY", 15*time.Minute); err != nil {
			log.Printf("[%s] ERROR waiting for primary %s to be READY: %v", cInsts.ClusterID, cInsts.Primary.Name, err)
			return
		}
		log.Printf("[%s] Primary %s is READY.", cInsts.ClusterID, cInsts.Primary.Name)
	}

	// 2. Start all Read Pools in parallel once Primary is READY
	if len(cInsts.ReadPools) > 0 {
		log.Printf("[%s] Initiating START for %d read pools...", cInsts.ClusterID, len(cInsts.ReadPools))
		var wg sync.WaitGroup
		for _, rp := range cInsts.ReadPools {
			wg.Add(1)
			go func(rpInst *Instance) {
				defer wg.Done()
				if err := startInstance(ctx, rpInst.Name); err != nil {
					log.Printf("[%s] ERROR starting read pool %s: %v", cInsts.ClusterID, rpInst.Name, err)
				}
				// Optionally wait for read pools too, but primary is the critical dependency.
				// Let's wait to ensure the cluster is fully "up" from this function's perspective.
				if err := waitForInstanceState(ctx, rpInst.Name, "READY", 15*time.Minute); err != nil {
					log.Printf("[%s] ERROR waiting for read pool %s to be READY: %v", cInsts.ClusterID, rpInst.Name, err)
				}
			}(rp)
		}
		wg.Wait()
	}
	log.Printf("[%s] Cluster start sequence completed.", cInsts.ClusterID)
}

func handleClusterStop(ctx context.Context, cInsts *ClusterInstances) {
	log.Printf("[%s] Stopping cluster...", cInsts.ClusterID)

	// 1. Stop all Read Pools first in parallel
	if len(cInsts.ReadPools) > 0 {
		log.Printf("[%s] Initiating STOP for %d read pools...", cInsts.ClusterID, len(cInsts.ReadPools))
		var wg sync.WaitGroup
		for _, rp := range cInsts.ReadPools {
			wg.Add(1)
			go func(rpInst *Instance) {
				defer wg.Done()
				if err := stopInstance(ctx, rpInst.Name); err != nil {
					log.Printf("[%s] ERROR stopping read pool %s: %v", cInsts.ClusterID, rpInst.Name, err)
					return
				}
				if err := waitForInstanceState(ctx, rpInst.Name, "STOPPED", 15*time.Minute); err != nil {
					log.Printf("[%s] ERROR waiting for read pool %s to be STOPPED: %v", cInsts.ClusterID, rpInst.Name, err)
				}
			}(rp)
		}
		wg.Wait()
		log.Printf("[%s] All read pools stopped.", cInsts.ClusterID)
	}

	// 2. Stop Primary after read pools are down
	if cInsts.Primary != nil {
		log.Printf("[%s] Initiating STOP for primary: %s", cInsts.ClusterID, cInsts.Primary.Name)
		if err := stopInstance(ctx, cInsts.Primary.Name); err != nil {
			log.Printf("[%s] ERROR stopping primary %s: %v", cInsts.ClusterID, cInsts.Primary.Name, err)
			return
		}
		if err := waitForInstanceState(ctx, cInsts.Primary.Name, "STOPPED", 15*time.Minute); err != nil {
			log.Printf("[%s] ERROR waiting for primary %s to be STOPPED: %v", cInsts.ClusterID, cInsts.Primary.Name, err)
		}
		log.Printf("[%s] Primary %s is STOPPED.", cInsts.ClusterID, cInsts.Primary.Name)
	}
	log.Printf("[%s] Cluster stop sequence completed.", cInsts.ClusterID)
}

// getOperation fetches the status of a long-running operation.
func getOperation(ctx context.Context, operationName string) (*Operation, error) {
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, fmt.Errorf("failed to create client: %v", err)
	}
	opURL := apiURL + "/" + operationName
	resp, err := client.Get(opURL)
	if err != nil {
		return nil, fmt.Errorf("failed to get operation %s: %v", operationName, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to get operation %s, status: %s, body: %s", operationName, resp.Status, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read operation response body: %v", err)
	}
	var op Operation
	if err := json.Unmarshal(body, &op); err != nil {
		return nil, fmt.Errorf("failed to unmarshal operation: %v", err)
	}
	return &op, nil
}

// waitForOperation polls an operation until it's done or times out.
func waitForOperation(ctx context.Context, operationName string, timeout time.Duration) error {
	log.Printf("Waiting for operation %s to complete...\n", operationName)
	timeoutChan := time.After(timeout)
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeoutChan:
			return fmt.Errorf("timeout reached while waiting for operation %s", operationName)
		case <-ticker.C:
			op, err := getOperation(ctx, operationName)
			if err != nil {
				log.Printf("could not get status for operation %s, retrying: %v", operationName, err)
				continue
			}

			if op.Done {
				if op.Error != nil {
					return fmt.Errorf("operation %s failed: %s (code %d)", operationName, op.Error.Message, op.Error.Code)
				}
				log.Printf("Operation %s completed successfully.\n", operationName)
				return nil
			}
		}
	}
}

// updateInstanceFlags sends a PATCH request to update database flags.
func updateInstanceFlags(ctx context.Context, instanceName string, flagsToUpdate map[string]string, debug bool) error {
	log.Printf("Updating flags for instance %s...", instanceName)
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return fmt.Errorf("failed to create client to update flags: %v", err)
	}

	instanceURL := apiURL + "/" + instanceName + "?updateMask=database_flags"

	type payload struct {
		DatabaseFlags map[string]string `json:"databaseFlags"`
	}
	p := payload{DatabaseFlags: flagsToUpdate}
	payloadBytes, err := json.Marshal(p)
	if err != nil {
		return fmt.Errorf("failed to marshal flags payload: %v", err)
	}

	if debug {
		log.Printf("DEBUG: updateInstanceFlags request body for %s: %s", instanceName, string(payloadBytes))
	}

	req, err := http.NewRequest("PATCH", instanceURL, strings.NewReader(string(payloadBytes)))
	if err != nil {
		return fmt.Errorf("failed to create update flags request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to execute update flags request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read update flags response: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("update flags request failed, status: %s, body: %s", resp.Status, string(body))
	}

	var op Operation
	if err := json.Unmarshal(body, &op); err != nil {
		return fmt.Errorf("failed to unmarshal update flags operation: %v", err)
	}

	log.Printf("Flag update initiated for %s. Operation: %s", instanceName, op.Name)
	return nil
}

// publishAlert sends a JSON message to a Pub/Sub topic.
func publishAlert(ctx context.Context, psClient *pubsub.Client, topicName string, alert AlertMessage) error {
	log.Printf("Publishing alert for %s to topic %s", alert.InstanceName, topicName)
	topic := psClient.Topic(topicName)

	alertBytes, err := json.Marshal(alert)
	if err != nil {
		return fmt.Errorf("failed to marshal alert message: %v", err)
	}

	result := topic.Publish(ctx, &pubsub.Message{
		Data: alertBytes,
	})

	if _, err := result.Get(ctx); err != nil {
		return fmt.Errorf("failed to publish alert to %s: %v", topicName, err)
	}
	return nil
}

// CheckAlloyDBInstances checks instances against a set of rules in parallel.
func CheckAlloyDBInstances(ctx context.Context, m PubSubMessage) error {
	var par CheckInstanceParams
	if err := json.Unmarshal(m.Data, &par); err != nil {
		log.Printf("CheckAlloyDBInstances: Failed to unmarshal json: %v", err)
		return err
	}

	if len(par.Rules) == 0 {
		log.Println("CheckAlloyDBInstances: No rules provided. Exiting.")
		return nil
	}

	log.Printf("Starting AlloyDB instances check for project %s", par.Project)

	// Create a shared Pub/Sub client for all goroutines if possible,
	// or let each one create its own if concurrency is high and sharing is bad.
	// Sharing is usually fine for moderate load.
	psClient, err := pubsub.NewClient(ctx, par.Project)
	if err != nil {
		log.Printf("CheckAlloyDBInstances: ERROR: Failed to create Pub/Sub client: %v", err)
		return err
	}
	defer psClient.Close()

	listedInstances, err := listInstances(ctx, par.Project, par.Location, par.Cluster)
	if err != nil {
		log.Printf("CheckAlloyDBInstances: ERROR: Failed to list instances: %v", err)
		return err
	}

	if len(listedInstances) == 0 {
		log.Println("CheckAlloyDBInstances: No instances found matching criteria.")
		return nil
	}

	log.Printf("CheckAlloyDBInstances: Found %d instances to check against %d rules.", len(listedInstances), len(par.Rules))

	var wg sync.WaitGroup
	for _, listedInstance := range listedInstances {
		wg.Add(1)
		go func(inst Instance) {
			defer wg.Done()
			checkAndRemediateInstance(ctx, psClient, inst, par.Rules, par.Debug)
		}(listedInstance)
	}

	wg.Wait()
	log.Println("CheckAlloyDBInstances: All instance checks completed.")
	return nil
}

// checkAndRemediateInstance processes a single instance: checks all rules, sends alerts, and consolidates flag updates.
func checkAndRemediateInstance(ctx context.Context, psClient *pubsub.Client, listedInstance Instance, rules []InstanceCheckRule, debug bool) {
	if listedInstance.State != "READY" {
		log.Printf("Skipping instance %s (state: %s)", listedInstance.Name, listedInstance.State)
		return
	}

	instanceDetails, err := getInstance(ctx, listedInstance.Name)
	if err != nil {
		log.Printf("ERROR: Failed to get details for instance %s: %v", listedInstance.Name, err)
		return
	}

	// Prepare to consolidate all flag updates for this instance.
	// Start with a copy of the current flags.
	flagsToUpdate := make(map[string]string)
	for k, v := range instanceDetails.DatabaseFlags {
		flagsToUpdate[k] = v
	}
	updatesNeeded := false

	for _, rule := range rules {
		var issueAlarm bool = false
		var alarmMsg, desiredValue string

		// --- Rule Checking Logic ---
		if rule.TargetFlagName == "max_connections" {
			var desiredValueInt, currentValueInt int
			var err error
			if rule.CorrectFlagValue != "" {
				desiredValueInt, err = strconv.Atoi(rule.CorrectFlagValue)
				if err != nil {
					log.Printf("ERROR: Invalid integer in rule.CorrectFlagValue for %s on %s: %v", rule.TargetFlagName, instanceDetails.Name, err)
					continue
				}
			} else {
				desiredValueInt = instanceDetails.MachineConfig.CpuCount * 400
			}
			desiredValue = strconv.Itoa(desiredValueInt)

			currentValueStr, ok := instanceDetails.DatabaseFlags[rule.TargetFlagName]
			if !ok {
				currentValueStr = "1000" // Default
			}
			currentValueInt, err = strconv.Atoi(currentValueStr)
			if err != nil {
				log.Printf("ERROR: Could not parse current flag value '%s' for %s on %s: %v", currentValueStr, rule.TargetFlagName, instanceDetails.Name, err)
				continue
			}

			if float64(currentValueInt) < 0.8*float64(desiredValueInt) || float64(currentValueInt) > 1.2*float64(desiredValueInt) {
				issueAlarm = true
				alarmMsg = fmt.Sprintf("Flag '%s' is set to %d, which is outside the 20%% tolerance of the recommended value %d.", rule.TargetFlagName, currentValueInt, desiredValueInt)
			}
		} else {
			// Generic flag check
			desiredValue = rule.CorrectFlagValue
			currentValue, ok := instanceDetails.DatabaseFlags[rule.TargetFlagName]
			if !ok {
				issueAlarm = true
				alarmMsg = fmt.Sprintf("Required flag '%s' is not set. Desired value is '%s'.", rule.TargetFlagName, desiredValue)
			} else if currentValue != desiredValue {
				issueAlarm = true
				alarmMsg = fmt.Sprintf("Flag '%s' has incorrect value. Current: '%s', Desired: '%s'.", rule.TargetFlagName, currentValue, desiredValue)
			}
		}

		// --- Remediation & Alerting ---
		if issueAlarm {
			fullAlarmMsg := fmt.Sprintf("Instance %s (%s): %s", instanceDetails.Name, instanceDetails.DisplayName, alarmMsg)
			log.Printf("ALERT: %s", fullAlarmMsg)

			// Schedule update if we have a desired value
			if desiredValue != "" {
				// Check if we are already planning to update this flag from another rule (unlikely but good to be safe)
				if existingPlan, ok := flagsToUpdate[rule.TargetFlagName]; ok && existingPlan != desiredValue {
					log.Printf("WARNING: Conflicting rules for flag '%s' on instance %s. Overwriting '%s' with '%s'.", rule.TargetFlagName, instanceDetails.Name, existingPlan, desiredValue)
				}
				flagsToUpdate[rule.TargetFlagName] = desiredValue
				updatesNeeded = true
			}

			// Send Alert immediately
			if rule.AlertTopic != "" {
				alertPayload := AlertMessage{
					InstanceName:              instanceDetails.Name,
					DisplayName:               instanceDetails.DisplayName,
					CheckRule:                 rule,
					Message:                   fullAlarmMsg,
					CorrectiveActionAttempted: desiredValue != "",
				}
				if err := publishAlert(ctx, psClient, rule.AlertTopic, alertPayload); err != nil {
					log.Printf("ERROR: Failed to publish alert for %s to %s: %v", instanceDetails.Name, rule.AlertTopic, err)
				}
			}
		}
	} // end rules loop

	// --- Apply Consolidated Updates ---
	if updatesNeeded {
		log.Printf("ACTION: Initiating consolidated flag update for %s", instanceDetails.Name)
		if err := updateInstanceFlags(ctx, instanceDetails.Name, flagsToUpdate, debug); err != nil {
			log.Printf("ERROR: Failed to initiate consolidated flag update for %s: %v", instanceDetails.Name, err)
		}
	}
}
