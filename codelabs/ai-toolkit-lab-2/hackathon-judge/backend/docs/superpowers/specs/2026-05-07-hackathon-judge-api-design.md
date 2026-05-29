# Hackathon Judge API Design

## Goal
Build a production-level Go API for a Hackathon Judging platform. The API will provide endpoints to retrieve hackathons and their associated projects.

## Architecture
We follow a **Pragmatic Clean Architecture** approach to ensure separation of concerns while maintaining development speed.

### Directory Structure
- `cmd/api/main.go`: Application entry point and dependency injection.
- `internal/domain/`: Entities and Repository/Service interfaces.
- `internal/repository/`: Data persistence (In-memory/Mock for now).
- `internal/service/`: Business logic.
- `internal/handler/`: Gin HTTP handlers and routing.
- `pkg/logger/`: Standard logger configuration.

## Data Models

### Hackathon
- `ID`: string (UUID)
- `Name`: string
- `Title`: string
- `Date`: time.Time
- `Description`: string
- `Goal`: string
- `Status`: string (Upcoming, Active, Closed)

### Project
- `ID`: string (UUID)
- `Name`: string
- `Title`: string
- `URL`: string
- `GitHubURL`: string
- `TeamName`: string
- `Document`: string
- `Date`: time.Time
- `HackathonID`: string (Relationship)
- `Score`: float64

## API Endpoints

### [GET] /api/hackathons
- **Description**: List all hackathons.
- **Response**: `200 OK` with JSON array of Hackathons.

### [GET] /api/hackathons/:id/projects
- **Description**: List all projects for a specific hackathon.
- **Response**: `200 OK` with JSON array of Projects.

## Tech Stack
- **Language**: Go 1.21+
- **Framework**: Gin Gonic
- **Logging**: Standard Library `log` package
- **Persistence**: In-memory mock storage
- **Testing**: `testify/assert`, `httptest`

## Testing Strategy
- **Unit Tests**: Test services in isolation using mock repositories.
- **Handler Tests**: Test API endpoints using `httptest` to verify routing, status codes, and JSON responses.
- **Mocking**: Use interfaces to swap in-memory storage with real DB in the future.

## Error Handling
- Standardized JSON error responses: `{"error": "message"}`.
- Middleware for panic recovery.
