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
	var primaryInstances []Instance
	var readPoolInstances []Instance
	for _, instance := range instances {
		if instance.InstanceType == "PRIMARY" {
			primaryInstances = append(primaryInstances, instance)
		} else if instance.InstanceType == "READ_POOL" {
			readPoolInstances = append(readPoolInstances, instance)
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
		fmt.Println("Executing STOP operation starting from read pool...")
		for _, rp := range readPoolInstances {
			if err := stopInstance(ctx, rp.Name); err != nil {
				log.Printf("error initiating stop for read pool instance %s: %v", rp.Name, err)
				continue
			}
			if err := waitForInstanceState(ctx, rp.Name, "STOPPED", 10*time.Minute); err != nil {
				log.Printf("error waiting for read pool %s to stop: %v", rp.Name, err)
				return err
			}
		}
		for _, p := range primaryInstances {
			if err := stopInstance(ctx, p.Name); err != nil {
				log.Printf("error stopping primary instance %s: %v", p.Name, err)
				continue
			}
			if err := waitForInstanceState(ctx, p.Name, "STOPPED", 10*time.Minute); err != nil {
				log.Printf("error waiting for primary %s to stop: %v", p.Name, err)
				return err
			}
		}
	case "START":
		fmt.Println("Executing START operation, primary first ...")
		if len(primaryInstances) > 0 {
			p := primaryInstances[0]
			if err := startInstance(ctx, p.Name); err != nil {
				log.Printf("error initiating start for primary instance %s: %v", p.Name, err)
				return err
			}
			if err := waitForInstanceState(ctx, p.Name, "READY", 10*time.Minute); err != nil {
				log.Printf("error waiting for primary %s to become ready: %v", p.Name, err)
				return err
			}
		} else {
			log.Println("No primary instance found to start.")
			return nil
		}
		for _, rp := range readPoolInstances {
			if err := startInstance(ctx, rp.Name); err != nil {
				log.Printf("error starting read pool instance %s: %v", rp.Name, err)
				continue
			}
			if err := waitForInstanceState(ctx, rp.Name, "READY", 10*time.Minute); err != nil {
				log.Printf("error waiting for read pool %s to become ready: %v", rp.Name, err)
			}
		}
	default:
		log.Printf("unknown operation requested: %s", instanceoperation)
	}
	fmt.Println("Done ManageAlloyDBInstances")
	return nil
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

	if err := waitForOperation(ctx, op.Name, 10*time.Minute); err != nil {
		return fmt.Errorf("error waiting for flag update operation: %v", err)
	}

	log.Printf("Flags updated successfully for %s", instanceName)
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

// CheckAlloyDBInstances checks instances against a set of rules.
// This function has been refactored to correctly implement the checking logic.
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

	log.Printf("Starting AlloyDB instance check for project %s", par.Project)

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
	var warningsFound int = 0

	for _, listedInstance := range listedInstances {
		if listedInstance.State != "READY" {
			log.Printf("CheckAlloyDBInstances: Skipping instance %s (state: %s)", listedInstance.Name, listedInstance.State)
			continue
		}

		instanceDetails, err := getInstance(ctx, listedInstance.Name)
		if err != nil {
			log.Printf("CheckAlloyDBInstances: ERROR: Failed to get details for instance %s: %v", listedInstance.Name, err)
			continue
		}

		for _, rule := range par.Rules {
			var issueAlarm bool = false
			var alarmMsg, currentValue, desiredValue string

			if rule.TargetFlagName == "max_connections" {
				// Special handling for max_connections
				var desiredValueInt, currentValueInt int
				var err error

				// Determine the desired value
				if rule.CorrectFlagValue != "" {
					desiredValueInt, err = strconv.Atoi(rule.CorrectFlagValue)
					if err != nil {
						log.Printf("CheckAlloyDBInstances: ERROR: Invalid integer in rule.CorrectFlagValue for %s: %v", rule.TargetFlagName, err)
						continue // Skip rule
					}
				} else {
					desiredValueInt = instanceDetails.MachineConfig.CpuCount * 400
				}
				desiredValue = strconv.Itoa(desiredValueInt)

				// Determine the current value
				currentValueStr, ok := instanceDetails.DatabaseFlags[rule.TargetFlagName]
				if !ok {
					currentValueStr = "1000" // Default value as per requirement
				}
				currentValue = currentValueStr
				currentValueInt, err = strconv.Atoi(currentValueStr)
				if err != nil {
					log.Printf("CheckAlloyDBInstances: ERROR: Could not parse current flag value '%s' for %s: %v", currentValueStr, rule.TargetFlagName, err)
					continue // Skip rule
				}

				// Check if an alarm needs to be issued
				if float64(currentValueInt) > 1.2*float64(desiredValueInt) {
					issueAlarm = true
					alarmMsg = fmt.Sprintf("Flag '%s' is set to %d, which is more than 120%% of the recommended value %d.", rule.TargetFlagName, currentValueInt, desiredValueInt)
				}

			} else {
				// Handling for all other flags
				desiredValue = rule.CorrectFlagValue
				currentValueStr, ok := instanceDetails.DatabaseFlags[rule.TargetFlagName]
				currentValue = currentValueStr

				if !ok {
					issueAlarm = true
					alarmMsg = fmt.Sprintf("Required flag '%s' is not set. Desired value is '%s'.", rule.TargetFlagName, desiredValue)
					currentValue = "[NOT SET]"
				} else if currentValue != desiredValue {
					issueAlarm = true
					alarmMsg = fmt.Sprintf("Flag '%s' has incorrect value. Current: '%s', Desired: '%s'.", rule.TargetFlagName, currentValue, desiredValue)
				}
			}

			// --- If an alarm was triggered, take action ---
			if issueAlarm {
				warningsFound++
				fullAlarmMsg := fmt.Sprintf("Instance %s (%s): %s", instanceDetails.Name, instanceDetails.DisplayName, alarmMsg)
				log.Printf("CheckAlloyDBInstances: ALERT: %s", fullAlarmMsg)

				correctionErrStr := ""
				correctionAttempted := false

				// Action 1: Fix the flag if a correct value is available
				if desiredValue != "" {
					correctionAttempted = true
					// The payload must include all existing flags, plus the updated one.
					allFlags := instanceDetails.DatabaseFlags
					if allFlags == nil {
						allFlags = make(map[string]string)
					}
					// Set the new/corrected value.
					allFlags[rule.TargetFlagName] = desiredValue

					log.Printf("CheckAlloyDBInstances: ACTION: Attempting to set flag '%s' to '%s' for %s", rule.TargetFlagName, desiredValue, instanceDetails.Name)

					if err := updateInstanceFlags(ctx, instanceDetails.Name, allFlags, par.Debug); err != nil {
						log.Printf("CheckAlloyDBInstances: ERROR: Failed to update flag for %s: %v", instanceDetails.Name, err)
						correctionErrStr = err.Error()
					} else {
						log.Printf("CheckAlloyDBInstances: ACTION: Successfully updated flag for %s", instanceDetails.Name)
					}
				}

				// Action 2: Send Pub/Sub Alert
				if rule.AlertTopic != "" {
					alertPayload := AlertMessage{
						InstanceName:              instanceDetails.Name,
						DisplayName:               instanceDetails.DisplayName,
						CheckRule:                 rule,
						Message:                   fullAlarmMsg,
						CorrectiveActionAttempted: correctionAttempted,
						CorrectionError:           correctionErrStr,
					}
					if err := publishAlert(ctx, psClient, rule.AlertTopic, alertPayload); err != nil {
						log.Printf("CheckAlloyDBInstances: ERROR: Failed to publish alert for %s: %v", instanceDetails.Name, err)
					}
				}
			}
		} // end rules loop
	} // end instances loop

	log.Printf("CheckAlloyDBInstances: Check complete. Found %d total warnings/actions.", warningsFound)
	return nil
}
