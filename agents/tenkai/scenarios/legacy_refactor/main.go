package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
)

// User represents a user in the system
type User struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}

var (
	users  = make(map[string]User)
	mutex  sync.RWMutex
	nextID = 1
)

func main() {
	http.HandleFunc("/users", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			mutex.RLock()
			var list []User
			for _, u := range users {
				list = append(list, u)
			}
			mutex.RUnlock()
			json.NewEncoder(w).Encode(list)

		case http.MethodPost:
			var u User
			if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			mutex.Lock()
			u.ID = fmt.Sprintf("%d", nextID)
			nextID++
			users[u.ID] = u
			mutex.Unlock()
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(u)

		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	http.HandleFunc("/users/", func(w http.ResponseWriter, r *http.Request) {
		id := r.URL.Path[len("/users/"):]
		switch r.Method {
		case http.MethodGet:
			mutex.RLock()
			u, ok := users[id]
			mutex.RUnlock()
			if !ok {
				http.NotFound(w, r)
				return
			}
			json.NewEncoder(w).Encode(u)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	log.Println("Server starting on :8080...")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatal(err)
	}
}
