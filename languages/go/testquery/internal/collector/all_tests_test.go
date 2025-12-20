package collector

import (
	"reflect"
	"testing"
	"time"
)

func TestParseTestOutput(t *testing.T) {
	inputJSON := `
{"Time":"2023-10-27T10:00:00Z","Action":"run","Package":"example.com/my/pkg","Test":"TestMyFunction"}
{"Time":"2023-10-27T10:00:01Z","Action":"pass","Package":"example.com/my/pkg","Test":"TestMyFunction","Elapsed":1.23}
{"Time":"2023-10-27T10:00:02Z","Action":"run","Package":"example.com/my/pkg","Test":"TestAnotherFunction"}
{"Time":"2023-10-27T10:00:03Z","Action":"fail","Package":"example.com/my/pkg","Test":"TestAnotherFunction","Elapsed":2.34}
`
	expectedTime1, _ := time.Parse(time.RFC3339, "2023-10-27T10:00:01Z")
	expectedTime2, _ := time.Parse(time.RFC3339, "2023-10-27T10:00:03Z")
	elapsed1 := 1.23
	elapsed2 := 2.34

	expected := []TestEvent{
		{Time: expectedTime1, Action: "pass", Package: "example.com/my/pkg", Test: "TestMyFunction", Elapsed: &elapsed1},
		{Time: expectedTime2, Action: "fail", Package: "example.com/my/pkg", Test: "TestAnotherFunction", Elapsed: &elapsed2},
	}

	// The function we are testing is collectTestResults, but the core logic to test is the parsing.
	// We will test the filtering logic separately.
	// For now, we test parseTestOutput which is called by collectTestResults.
	
	// Re-create the logic from collectTestResults to filter for only pass/fail events.
	allEvents, err := parseTestOutput([]byte(inputJSON))
	if err != nil {
		t.Fatalf("parseTestOutput failed: %v", err)
	}

	var got []TestEvent
	for _, event := range allEvents {
		if event.Test == "" || (event.Action != "pass" && event.Action != "fail") {
			continue
		}
		got = append(got, event)
	}

	if !reflect.DeepEqual(got, expected) {
		t.Errorf("parseTestOutput() got = %v, want %v", got, expected)
	}
}
