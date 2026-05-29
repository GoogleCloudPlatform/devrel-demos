# Evaluation Model Design

## Goal
Add the ability to track individual judge scores for projects using a variable criteria system. The system must support weights for different criteria and calculate an overall average score for the project.

## Data Models

### CriteriaScore
Represents a single score for a specific criterion given by a judge.
- `Name`: string (e.g., "Design", "Technical Complexity")
- `Score`: float64 (The raw score given)
- `Weight`: float64 (The weight of this criterion in the overall evaluation)

### Evaluation
Represents a complete review of a project by a single judge.
- `ID`: string (UUID)
- `ProjectID`: string (Foreign key to Project)
- `JudgeID`: string (Identifier for the judge)
- `Criteria`: []CriteriaScore (List of all criteria scored)
- `TotalScore`: float64 (Calculated: sum of `Score * Weight` for all criteria)
- `Comment`: string (Optional feedback)
- `CreatedAt`: time.Time

### Project (Updates)
- The existing `Score` field on the `Project` model will be retained.
- It will now represent the **calculated average** of all `TotalScore` values from the `Evaluation` records associated with the project.

## Architecture & Data Flow
1. **Domain Layer**: The new structs (`Evaluation`, `CriteriaScore`) will be added to `internal/domain/evaluation.go`.
2. **Repository Layer**: A new `EvaluationRepository` interface will be created to save and retrieve evaluations by ProjectID.
3. **Calculation Logic**: When a new `Evaluation` is added, its `TotalScore` is calculated. The system should then recalculate the average `Score` for the associated `Project`.

## Note on Implementation Scope
This design document specifically addresses the data modeling of the evaluation system. The implementation of specific API endpoints to submit evaluations is outside the immediate scope unless requested, but the data structures will support it.
