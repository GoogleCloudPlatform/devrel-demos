# Judging Criteria Refactor Design

## Goal
Move the definition of judging criteria from individual evaluations to the Hackathon level. This allows event organizers to define a consistent rubric for the event, while evaluations simply record scores and reasoning against that rubric.

## Data Models

### Criterion (New Template)
Represents a grading dimension defined at the Hackathon level.
- `Name`: string (e.g., "Technology", "Design")
- `Weight`: float64 (Multiplier for the score)
- `Description`: string (Optional rubric describing what the levels mean in practice, e.g., "1-barely works, 5-really good tested")

### Hackathon (Update)
- `Criteria`: []Criterion (The template of criteria for all projects in this event)

### CriteriaScore (Update)
Represents a single score given by a judge against a specific criterion template.
- `Name`: string (Matches a Criterion name from the Hackathon)
- `Score`: float64 (The raw score given, e.g., 1-5)
- `Reasoning`: string (Optional field for the judge to explain why they gave this score)
- *Note:* `Weight` is removed from here as it is defined by the Hackathon.

### Evaluation (Update)
- `TotalScore`: float64 (Calculated: sum of `Score * Hackathon.Criteria.Weight` for all submitted criteria)

## Architecture & Data Flow
1. **Domain Layer**: 
    - Add `Criterion` struct to `internal/domain/hackathon.go`.
    - Update `Hackathon` struct to include `Criteria []Criterion`.
    - Update `CriteriaScore` struct in `internal/domain/evaluation.go` to remove `Weight` and add `Reasoning`.
2. **Service Layer**:
    - Update `Evaluation` `TotalScore` calculation logic in `HackathonService.AddEvaluation`. 
    - When an evaluation is added, the service must fetch the `Project` to get the `HackathonID`, then fetch the `Hackathon` to access the weights.
3. **Repository Layer**:
    - Update memory mock data in `internal/repository/memory_repo.go` to reflect the new structure.

## Note
This is an amendment to the previous evaluation and hackathon design documents.
