package main

import (
	"fmt"
	"testing"
	"time"
)

func TestProcessJobs(t *testing.T) {
	numJobs := 1000
	numWorkers := 10

	done := make(chan struct{})
	var count int
	var err error

	go func() {
		count, err = ProcessJobs(numJobs, numWorkers)
		close(done)
	}()

	select {
	case <-done:
		if err != nil {
			t.Fatalf("ProcessJobs returned error: %v", err)
		}
		// Check for race condition evidence (count mismatch)
		// With 1000 jobs and a race, count is usually < 1000.
		if count != numJobs {
			t.Errorf("Race Condition detected? Expected %d processed jobs, got %d", numJobs, count)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Deadlock detected! ProcessJobs timed out after 2s")
	}
	fmt.Printf("Test passed: Processed %d jobs without deadlock.\n", count)
}
