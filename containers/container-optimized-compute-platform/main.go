// Copyright 2025 Google LLC
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
	"log"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/watch"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest" // For in-cluster config
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/util/homedir"
)

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			// Since the Go server is serving the frontend, origin will be the same.
			// Allowing all origins is okay here, but you could check against the expected host.
			return true
		},
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
	}

	clients = make(map[*websocket.Conn]bool)
	mutex   = &sync.Mutex{}

	latestReplicaCount int32 = 1

	// Configuration for the target deployment - loaded from environment variables
	targetDeploymentName      = os.Getenv("TARGET_DEPLOYMENT_NAME")
	targetDeploymentNamespace = os.Getenv("TARGET_DEPLOYMENT_NAMESPACE")

	// Directory where the static Next.js files are located within the container/local filesystem
	staticFilesDir = os.Getenv("STATIC_FILES_DIR") // e.g., "/app/out"
	local          = os.Getenv("LOCAL")
)

func main() {

	if targetDeploymentName == "" || targetDeploymentNamespace == "" {
		// log.Fatal("TARGET_DEPLOYMENT_NAME and TARGET_DEPLOYMENT_NAMESPACE environment variables must be set")
		targetDeploymentName = "echoserver"
		targetDeploymentNamespace = "echoserver"
	}
	if staticFilesDir == "" {
		// log.Fatal("STATIC_FILES_DIR environment variable must be set to the path of Next.js static files")
		staticFilesDir = "client/out"
	}
	if local == "" {
		local = "true"
	}

	log.Printf("Targeting deployment %s/%s for scaling and monitoring", targetDeploymentNamespace, targetDeploymentName)
	log.Printf("Serving static files from directory: %s", staticFilesDir)

	// --- Initialize Kubernetes client ---
	// This function attempts to use in-cluster config, which is standard for Pods in K8s.

	var clientset *kubernetes.Clientset
	var err error

	if local == "true" {
		home := homedir.HomeDir()
		kubeconfig := filepath.Join(home, ".kube", "config")
		config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			log.Fatalf("Failed to build config from ~/.kube/config: %v", err)
		}
		clientset, err = kubernetes.NewForConfig(config)
	} else {
		clientset, err = getKubernetesClient()
		if err != nil {
			log.Fatalf("Failed to create Kubernetes client: %v", err)
		}
	}

	log.Println("Kubernetes client initialized successfully.")
	// --- HTTP and WebSocket Server Setup ---

	// --- Start background K8s watch goroutine ---
	// This goroutine will continuously monitor the target deployment for replica changes.
	go watchTargetDeployment(clientset, targetDeploymentName, targetDeploymentNamespace)

	// Handler for the game start trigger
	http.HandleFunc("/api/start", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Only POST method is allowed", http.StatusMethodNotAllowed)
			return
		}
		log.Printf("Received /start request from %s", r.RemoteAddr)

		// Scale the target deployment to 50 replicas
		err := scaleDeployment(clientset, targetDeploymentName, targetDeploymentNamespace, 50)
		if err != nil {
			log.Printf("Error scaling deployment: %v", err)
			// Return a 500 Internal Server Error response
			http.Error(w, fmt.Sprintf("Failed to scale deployment: %v", err), http.StatusInternalServerError)
			return
		}

		log.Printf("Successfully triggered scale up for deployment %s/%s to 50 replicas", targetDeploymentNamespace, targetDeploymentName)
		// Return a success response
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, "Scale up triggered successfully")
	})

	http.HandleFunc("/api/stop", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "Only POST method is allowed", http.StatusMethodNotAllowed)
			return
		}
		log.Printf("Received /stop request from %s", r.RemoteAddr)

		// Scale the target deployment to 50 replicas
		err := scaleDeployment(clientset, targetDeploymentName, targetDeploymentNamespace, 1)
		if err != nil {
			log.Printf("Error scaling deployment: %v", err)
			// Return a 500 Internal Server Error response
			http.Error(w, fmt.Sprintf("Failed to scale deployment: %v", err), http.StatusInternalServerError)
			return
		}

		log.Printf("Successfully triggered scale up for deployment %s/%s to 50 replicas", targetDeploymentNamespace, targetDeploymentName)
		// Return a success response
		w.WriteHeader(http.StatusOK)
		fmt.Fprintln(w, "Scale down triggered successfully")
	})

	// Handler for WebSocket connections
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		// Upgrade the HTTP connection to a WebSocket connection
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("Failed to upgrade to websocket: %v", err)
			return
		}
		// Ensure the connection is closed when the handler exits
		defer conn.Close()

		log.Printf("New WebSocket connection from %s", conn.RemoteAddr())

		// Add the new client to our map of connected clients
		mutex.Lock()
		clients[conn] = true
		mutex.Unlock()

		// Send the current replica count to the newly connected client immediately
		sendReplicaCountToClient(conn, latestReplicaCount)

		// Keep the connection open. This loop listens for messages from the client.
		// In this application, the client doesn't send messages, but this loop
		// is necessary to detect when the client disconnects.
		for {
			// ReadMessage is a blocking call. It will return an error when the connection is closed.
			messageType, p, err := conn.ReadMessage()
			if err != nil {
				log.Printf("ReadMessage error for client %s: %v (ErrorType: %T)", conn.RemoteAddr(), err, err)
				// Check if the error is a normal WebSocket close error
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseNormalClosure) {
					log.Printf("WebSocket UNEXPECTED close error from %s: %v", conn.RemoteAddr(), err)
				} else {
					log.Printf("WebSocket NORMAL close/error by client %s: %v", conn.RemoteAddr(), err)
				}
				break // Exit the loop on error (client disconnected)
			}
			log.Printf("Received message from client %s: Type=%d, Payload=%s", conn.RemoteAddr(), messageType, string(p))
			// If you expected messages from the client, process them here.
			// For this app, we don't expect client messages.
		}

		// Remove the client from the map when the connection is closed
		mutex.Lock()
		delete(clients, conn)
		mutex.Unlock()
		log.Printf("WebSocket client disconnected: %s (after read loop)", conn.RemoteAddr())
	})

	// --- Serve Static Files ---
	// Create a file server handler that serves files from the specified directory.
	// http.Dir ensures the path is treated as a directory.
	fileServer := http.FileServer(http.Dir(staticFilesDir))

	// Handle all other requests by serving static files.
	// This handler will check if the requested path exists as a file in staticFilesDir.
	// If it does, it serves the file. If not, it might serve index.html for SPAs,
	// or return a 404. For Next.js static export, it handles routing based on file structure.
	http.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Important for SPAs or Next.js static exports: if a path like /game
		// doesn't map directly to a file, you often want to serve index.html
		// and let the client-side router handle it. Next.js static export
		// handles this somewhat automatically if you navigate to /game and it
		// exists as out/game/index.html. For / (root), it serves out/index.html.
		// The http.FileServer handles index.html automatically for directories.

		// Prevent directory listing
		if _, err := os.Stat(filepath.Join(staticFilesDir, r.URL.Path)); os.IsNotExist(err) && r.URL.Path != "/" {
			// If the requested path doesn't exist as a file/directory,
			// and it's not the root, check if index.html exists for that path
			// (e.g., request for /about serves /out/about/index.html)
			indexPath := filepath.Join(staticFilesDir, r.URL.Path, "index.html")
			if _, err := os.Stat(indexPath); !os.IsNotExist(err) {
				// Serve the index.html for the sub-path
				http.ServeFile(w, r, indexPath)
				return
			}
			// If index.html for the sub-path doesn't exist, check if root index.html exists
			indexPath = filepath.Join(staticFilesDir, "index.html")
			if _, err := os.Stat(indexPath); !os.IsNotExist(err) {
				// Serve the root index.html for any unmatched path (common for SPAs)
				http.ServeFile(w, r, indexPath)
				return
			}
		}

		// Serve the file using the standard file server
		fileServer.ServeHTTP(w, r)
	}))

	// --- Start HTTP Server ---
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080" // Default port
	}
	listenAddr := fmt.Sprintf(":%s", port)
	log.Printf("Starting HTTP and WebSocket server on %s", listenAddr)
	err = http.ListenAndServe(listenAddr, nil)
	if err != nil {
		log.Fatalf("HTTP server failed: %v", err)
	}
}

// getKubernetesClient sets up the Kubernetes client configuration.
// It prioritizes in-cluster configuration (for running inside a Pod).
// If in-cluster config fails, it will attempt to use the local kubeconfig file
// (useful for local development/testing outside the cluster).
func getKubernetesClient() (*kubernetes.Clientset, error) {
	// Try to get in-cluster config (standard for Pods)
	config, err := rest.InClusterConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to get in-cluster config: %w", err)
	}

	// Create the clientset
	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create clientset: %w", err)
	}
	return clientset, nil
}

// scaleDeployment updates the replica count of a specified Kubernetes deployment.
func scaleDeployment(clientset *kubernetes.Clientset, name, namespace string, replicas int32) error {
	// Get the Deployments client for the specified namespace
	deploymentsClient := clientset.AppsV1().Deployments(namespace)

	// Get the current state of the deployment
	deployment, err := deploymentsClient.Get(context.TODO(), name, metav1.GetOptions{})
	if err != nil {
		return fmt.Errorf("failed to get deployment %s/%s: %w", namespace, name, err)
	}

	// Update the replica count in the deployment spec
	deployment.Spec.Replicas = &replicas // Use a pointer to the replica count

	// Send the updated deployment object back to the Kubernetes API
	_, err = deploymentsClient.Update(context.TODO(), deployment, metav1.UpdateOptions{})
	if err != nil {
		return fmt.Errorf("failed to update deployment %s/%s: %w", namespace, name, err)
	}

	log.Printf("Sent update request to scale deployment %s/%s to %d replicas", namespace, name, replicas)
	return nil
}

// watchTargetDeployment watches the specified deployment for status changes
// and broadcasts the ready replica count to all connected WebSocket clients.
func watchTargetDeployment(clientset *kubernetes.Clientset, name, namespace string) {
	deploymentsClient := clientset.AppsV1().Deployments(namespace)

	// Use the Watch API to get a stream of events for the specific deployment
	// We filter by the deployment name using FieldSelector for efficiency
	watcher, err := deploymentsClient.Watch(context.TODO(), metav1.ListOptions{
		FieldSelector: fmt.Sprintf("metadata.name=%s", name),
	})
	if err != nil {
		log.Printf("Failed to set up watch for deployment %s/%s: %v", namespace, name, err)
		// If watch fails, attempt to restart it after a delay
		time.Sleep(10 * time.Second)
		go watchTargetDeployment(clientset, name, namespace) // Recursive call to restart
		return                                               // Exit the current goroutine
	}
	defer watcher.Stop() // Ensure the watcher is stopped when the function exits

	log.Printf("Started watching deployment %s/%s for status updates", namespace, name)

	// Process events received from the watch channel
	for event := range watcher.ResultChan() {
		// We are only interested in Modified events for Deployments
		if event.Type != watch.Modified && event.Type != watch.Added {
			// log.Printf("Ignoring event type: %s", event.Type)
			continue // Skip events that are not modifications or initial adds
		}

		// Attempt to cast the received object to a Deployment
		dep, ok := event.Object.(*appsv1.Deployment)
		if !ok {
			log.Printf("Received unexpected object type from watch: %T", event.Object)
			continue // Skip if it's not a Deployment
		}

		// Extract the ready replica count from the Deployment status
		// ReadyReplicas is a good indicator of how many pods are available to serve requests
		newReplicaCount := dep.Status.ReadyReplicas

		// Check if the replica count has actually changed since the last update
		if newReplicaCount != latestReplicaCount {
			latestReplicaCount = newReplicaCount // Update the latest count
			log.Printf("Observed new ready replica count for %s/%s: %d", namespace, name, latestReplicaCount)
			// Broadcast the new count to all connected WebSocket clients
			broadcastReplicaCount(latestReplicaCount)
		}

		// Optional: If you want the watch to stop once the target count is reached
		if latestReplicaCount >= 50 {
			log.Printf("Target replica count (%d) reached, stopping watch.", latestReplicaCount)
			// watcher.Stop() // Stop this specific watch instance
			// return // Exit goroutine
		}
	}

	// If the loop finishes (e.g., the watch channel closes unexpectedly), attempt to restart the watch
	log.Printf("Kubernetes watch for deployment %s/%s stopped unexpectedly. Attempting restart...", namespace, name)
	time.Sleep(5 * time.Second)                          // Wait before attempting restart
	go watchTargetDeployment(clientset, name, namespace) // Restart the watch
}

// broadcastReplicaCount sends the current replica count to all connected WebSocket clients.
func broadcastReplicaCount(count int32) {
	// Create a JSON message with the replica count
	message, err := json.Marshal(map[string]int32{"replicas": count})
	if err != nil {
		log.Printf("Broadcast: Error marshalling replica count to JSON: %v", err)
		return
	}
	log.Printf("Broadcast: Preparing to send replica count %d to %d clients. Message: %s", count, len(clients), string(message))

	// Iterate over all connected clients and send the message
	mutex.Lock()         // Lock the mutex before accessing the clients map
	defer mutex.Unlock() // Ensure mutex is unlocked when the function exits

	// Create a slice to hold clients to remove (those that failed to send)
	clientsToRemove := []*websocket.Conn{}

	for client := range clients {
		log.Printf("Broadcast: Attempting to send message to client %s", client.RemoteAddr())
		err := client.WriteMessage(websocket.TextMessage, message)
		if err != nil {
			log.Printf("Broadcast: Error sending message to client %s: %v. Marking for removal.", client.RemoteAddr(), err)
			// If sending fails, assume the client is disconnected and mark for removal
			client.Close() // Attempt to close the connection cleanly
			clientsToRemove = append(clientsToRemove, client)
		} else {
			log.Printf("Broadcast: Successfully sent message to client %s", client.RemoteAddr())
		}
	}

	// Remove failed clients from the map
	if len(clientsToRemove) > 0 {
		log.Printf("Broadcast: Removing %d disconnected client(s) after send failures.", len(clientsToRemove))
		for _, client := range clientsToRemove {
			delete(clients, client)
			log.Printf("Broadcast: Removed client %s", client.RemoteAddr())
		}
	}
}

// sendReplicaCountToClient sends the current replica count to a single specified client.
// Useful for sending the initial count when a client connects.
func sendReplicaCountToClient(client *websocket.Conn, count int32) {
	message, err := json.Marshal(map[string]int32{"replicas": count})
	if err != nil {
		log.Printf("InitialSend: Error marshalling initial replica count to JSON for %s: %v", client.RemoteAddr(), err)
		return
	}
	log.Printf("InitialSend: Preparing to send replica count %d to client %s. Message: %s", count, client.RemoteAddr(), string(message))

	mutex.Lock() // Lock before writing to the client connection
	// defer mutex.Unlock() // Unlock will be handled before return or if WriteMessage panics (though unlikely)

	log.Printf("InitialSend: Attempting to send message to client %s", client.RemoteAddr())
	err = client.WriteMessage(websocket.TextMessage, message)
	if err != nil {
		log.Printf("InitialSend: Error sending message to client %s: %v. Closing and removing.", client.RemoteAddr(), err)
		client.Close()
		delete(clients, client) // Remove client on error
		mutex.Unlock()          // Unlock before returning due to error
		return
	}
	mutex.Unlock() // Unlock after successful write
	log.Printf("InitialSend: Successfully sent message to client %s", client.RemoteAddr())
}
