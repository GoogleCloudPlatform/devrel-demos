package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"

	"alloydb.instances.manager/p"
)

func main() {
	manageCmd := flag.NewFlagSet("manage", flag.ExitOnError)
	checkCmd := flag.NewFlagSet("check", flag.ExitOnError)

	manageProject := manageCmd.String("project", "", "GCP Project ID")
	manageLocation := manageCmd.String("location", "ALL", "AlloyDB location")
	manageCluster := manageCmd.String("cluster", "ALL", "AlloyDB cluster")
	manageOperation := manageCmd.String("operation", "LIST", "Operation to perform (LIST, FAILOVER, DELETE, STOP, START)")

	checkProject := checkCmd.String("project", "", "GCP Project ID")
	checkLocation := checkCmd.String("location", "ALL", "AlloyDB location")
	checkCluster := checkCmd.String("cluster", "ALL", "AlloyDB cluster")
	checkInstance := checkCmd.String("instance", "ALL", "AlloyDB instance")
	checkRules := checkCmd.String("rules", "", "JSON string of check rules")
	checkDebug := checkCmd.Bool("debug", false, "true to enable debug")

	if len(os.Args) < 2 {
		fmt.Println("expected 'manage' or 'check' subcommands")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "manage":
		manageCmd.Parse(os.Args[2:])
		params := p.Parameters{
			Project:   *manageProject,
			Location:  *manageLocation,
			Operation: *manageOperation,
			Cluster:   *manageCluster,
		}
		data, err := json.Marshal(params)
		if err != nil {
			log.Fatalf("Failed to marshal manage params: %v", err)
		}
		msg := p.PubSubMessage{Data: data}
		if err := p.ManageAlloyDBInstances(context.Background(), msg); err != nil {
			log.Fatalf("ManageAlloyDBInstances failed: %v", err)
		}
	case "check":
		checkCmd.Parse(os.Args[2:])
		var rules []p.InstanceCheckRule
		if *checkRules != "" {
			if err := json.Unmarshal([]byte(*checkRules), &rules); err != nil {
				log.Fatalf("Failed to unmarshal check rules: %v", err)
			}
		}
		params := p.CheckInstanceParams{
			Project:  *checkProject,
			Location: *checkLocation,
			Cluster:  *checkCluster,
			Instance: *checkInstance,
			Rules:    rules,
			Debug:    *checkDebug,
		}
		data, err := json.Marshal(params)
		if err != nil {
			log.Fatalf("Failed to marshal check params: %v", err)
		}
		msg := p.PubSubMessage{Data: data}
		if err := p.CheckAlloyDBInstances(context.Background(), msg); err != nil {
			log.Fatalf("CheckAlloyDBInstances failed: %v", err)
		}
	default:
		fmt.Println("expected 'manage' or 'check' subcommands")
		os.Exit(1)
	}
}
