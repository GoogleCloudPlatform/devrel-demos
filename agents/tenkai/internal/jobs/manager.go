package jobs

import (
	"sync"
	"time"

	"github.com/google/uuid"
)

type JobStatus string

const (
	StatusRunning   JobStatus = "RUNNING"
	StatusCompleted JobStatus = "COMPLETED"
	StatusFailed    JobStatus = "FAILED"
)

type Job struct {
	ID        string    `json:"id"`
	Type      string    `json:"type"`
	Status    JobStatus `json:"status"`
	Progress  int       `json:"progress"` // 0-100
	Total     int       `json:"total"`
	Completed int       `json:"completed"`
	Error     string    `json:"error,omitempty"`
	Meta      any       `json:"meta,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type Manager struct {
	mu   sync.RWMutex
	jobs map[string]*Job
}

var globalManager *Manager
var once sync.Once

func GetManager() *Manager {
	once.Do(func() {
		globalManager = &Manager{
			jobs: make(map[string]*Job),
		}
	})
	return globalManager
}

func (m *Manager) CreateJob(jobType string, meta any) *Job {
	m.mu.Lock()
	defer m.mu.Unlock()

	id := uuid.New().String()
	job := &Job{
		ID:        id,
		Type:      jobType,
		Status:    StatusRunning,
		Meta:      meta,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
	m.jobs[id] = job
	return job
}

func (m *Manager) GetJob(id string) *Job {
	m.mu.RLock()
	defer m.mu.RUnlock()
	if job, ok := m.jobs[id]; ok {
		// Return copy to avoid race on read?
		// For simple UI polling, returning pointer is mostly fine if we don't modify it outside lock.
		// Use a copy to be safe.
		j := *job
		return &j
	}
	return nil
}

func (m *Manager) UpdateProgress(id string, completed, total int) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if job, ok := m.jobs[id]; ok {
		job.Completed = completed
		job.Total = total
		if total > 0 {
			job.Progress = int((float64(completed) / float64(total)) * 100)
		}
		job.UpdatedAt = time.Now()
	}
}

func (m *Manager) CompleteJob(id string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if job, ok := m.jobs[id]; ok {
		job.Status = StatusCompleted
		job.Progress = 100
		job.UpdatedAt = time.Now()
	}
}

func (m *Manager) FailJob(id string, err error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if job, ok := m.jobs[id]; ok {
		job.Status = StatusFailed
		job.Error = err.Error()
		job.UpdatedAt = time.Now()
	}
}
