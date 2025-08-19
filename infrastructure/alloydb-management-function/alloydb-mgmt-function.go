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
	"strings"
	"time"

	"golang.org/x/oauth2/google"
)

// PubSubMessage is the payload of a Pub/Sub event. Please refer to the docs for
// additional information regarding Pub/Sub events.
type PubSubMessage struct {
	Data []byte `json:"data"`
}
type Parameters struct {
	Project   string `json:"project"`
	Location  string `json:"location"`
	Operation string `json:"operation"`
	Cluster   string `json:"cluster"`
	Instance  string `json:"instance"`
	Retention int    `json:"retention"`
}

var apiURL string = "https://alloydb.googleapis.com/v1beta"

// List of AlloyDB instances from API response
type Instances struct {
	Instances []Instance `json:"instances"`
}

// A single instance from the list
type Instance struct {
	Name         string `json:"name"`
	DisplayName  string `json:"displayName"`
	Uid          string `json:"uid"`
	CreateTime   string `json:"createTime"`
	UpdateTime   string `json:"updateTime"`
	DeleteTime   string `json:"deleteTime"`
	State        string `json:"state"`
	InstanceType string `json:"instanceType"`
	Description  string `json:"description"`
	IpAddress    string `json:"ipAddress"`
	Reconciling  bool   `json:"reconciling"`
	Etag         string `json:"etag"`
}

// List of available locations
type Locations struct {
	Locations []Location `json:"locations"`
}

// Location is a single location
type Location struct {
	Name        string `json:"name"`
	LocationId  string `json:"locationId"`
	DisplayName string `json:"displayName"`
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
	// Listing all instances
	lstInst := []Instance{}
	fmt.Println("Listing all instances")
	client, err := google.DefaultClient(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err != nil {
		return nil, fmt.Errorf("failed to create default client: %v", err)
	}
	var instancesURL string
	if location == "ALL" {
		if cluster == "ALL" {
			// Get URL for list of all instances for all clusters in all locations
			instancesURL = fmt.Sprintf("%s/projects/%s/locations/-/clusters/-/instances", apiURL, project)
		} else {
			// Get list of all locations instances for clusters with defined name in all locations
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
			for _, location := range locations.Locations {
				//fmt.Println(location.LocationId)
				instancesURL = fmt.Sprintf("%s/projects/%s/locations/%s/clusters/%s/instances", apiURL, project, location.LocationId, cluster)
				resp, err := client.Get(instancesURL)
				if err != nil {
					log.Printf("could not get instances for cluster %s in location %s: %v", cluster, location.LocationId, err)
					continue
				}
				defer resp.Body.Close()
				instancesListBody, err := io.ReadAll(resp.Body)
				if err != nil {
					log.Printf("could not read instance body for cluster %s in location %s: %v", cluster, location.LocationId, err)
				}

				instances := Instances{}
				if err = json.Unmarshal(instancesListBody, &instances); err == nil && len(instances.Instances) > 0 {
					lstInst = append(lstInst, instances.Instances...)

				}
			}
			return lstInst, nil

		}

	} else {
		// Get list of all instances for all clusters in a particular location
		if cluster == "ALL" {
			//
			instancesURL = apiURL + "/projects/" + project + "/locations/" + location + "/clusters/-/instances"
			fmt.Println(instancesURL)
		} else {
			// Get list of all instances for a clusters with defined name in a particular location
			instancesURL = apiURL + "/projects/" + project + "/locations/" + location + "/clusters/" + cluster + "/instances"
			fmt.Println(instancesURL)
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
	// Delete an instance
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
	fmt.Println("Delete Response", resp.Status)
	return nil
}
// failoverInstance post a request to failover an instance.
func failoverInstance(ctx context.Context, instance string) error {
	// Failover an instance
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
	//Parameters
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
	// Separate instances by type for start/stop operations
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
		for _, instance := range instances{
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
		// Stop read pools one by one
		for _, rp := range readPoolInstances {
			if err := stopInstance(ctx, rp.Name); err != nil {
				log.Printf("error initiating stop for read pool instance %s: %v", rp.Name, err)
				continue // Try next instance even if one fails
			}
			if err := waitForInstanceState(ctx, rp.Name, "STOPPED", 10*time.Minute); err != nil {
				log.Printf("error waiting for read pool %s to stop: %v", rp.Name, err)
				// Decide if you want to continue or stop the whole process
				return err
			}
		}

		// Stop primary instance last
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
		// Poll until primary is ready
		if len(primaryInstances) > 0 {
			p := primaryInstances[0]
			if err := startInstance(ctx, p.Name); err != nil {
				log.Printf("error initiating start for primary instance %s: %v", p.Name, err)
				return err // If primary fails to start, do not proceed
			}
			if err := waitForInstanceState(ctx, p.Name, "READY", 10*time.Minute); err != nil {
				log.Printf("error waiting for primary %s to become ready: %v", p.Name, err)
				return err
			}
		} else {
			log.Println("No primary instance found to start.")
			return nil
		}
		// Start read pools one by one
		for _, rp := range readPoolInstances {
			if err := startInstance(ctx, rp.Name); err != nil {
				log.Printf("error starting read pool instance %s: %v", rp.Name, err)
				continue // Try next instance
			}
			if err := waitForInstanceState(ctx, rp.Name, "READY", 10*time.Minute); err != nil {
				log.Printf("error waiting for read pool %s to become ready: %v", rp.Name, err)
				// Decide if you want to continue or stop
			}
		}
	default:
		log.Printf("unknown operation requested: %s", instanceoperation)
	}
	fmt.Println("Done ManageAlloyDBInstances")
	return nil
}