package main

import (
	"log"
	"net/http"
)

func main() {
	addr := ":8080"
	log.Printf("Serving Cloud Crush at http://localhost%s", addr)
	// Serve files from the public directory
	if err := http.ListenAndServe(addr, http.FileServer(http.Dir("public"))); err != nil {
		log.Fatal(err)
	}
}
