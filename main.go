package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// PipelineStage represents a stage in the CI/CD pipeline
type PipelineStage string

const (
	StageTest    PipelineStage = "test"
	StageBuild   PipelineStage = "build"
	StageDeploy  PipelineStage = "deploy"
	StageMonitor PipelineStage = "monitor"
)

// PipelineExecution represents a single pipeline run
type PipelineExecution struct {
	ID          string         `json:"id"`
	Pipeline    string         `json:"pipeline"`
	Stage       PipelineStage  `json:"stage"`
	Status      string         `json:"status"` // pending, running, success, failed
	StartedAt   time.Time      `json:"started_at"`
	FinishedAt  *time.Time     `json:"finished_at,omitempty"`
	DurationMs  int64          `json:"duration_ms"`
	Logs        []string       `json:"logs"`
	Artifacts   []string       `json:"artifacts"`
	Environment string         `json:"environment"`
}

// PipelineOrchestrator orchestrates CI/CD pipelines
type PipelineOrchestrator struct {
	mu          sync.RWMutex
	executions  map[string]*PipelineExecution
	pipelines   map[string][]PipelineStage
	deployments map[string]string // env -> version
}

func NewPipelineOrchestrator() *PipelineOrchestrator {
	return &PipelineOrchestrator{
		executions:  make(map[string]*PipelineExecution),
		pipelines:   make(map[string][]PipelineStage),
		deployments: make(map[string]string),
	}
}

func (o *PipelineOrchestrator) RegisterPipeline(name string, stages []PipelineStage) {
	o.mu.Lock()
	defer o.mu.Unlock()
	o.pipelines[name] = stages
}

func (o *PipelineOrchestrator) StartExecution(pipeline string, env string) *PipelineExecution {
	o.mu.Lock()
	defer o.mu.Unlock()

	exec := &PipelineExecution{
		ID:          fmt.Sprintf("%s-%d", pipeline, time.Now().UnixNano()),
		Pipeline:    pipeline,
		Stage:       StageTest,
		Status:      "running",
		StartedAt:   time.Now(),
		Environment: env,
		Logs:        []string{fmt.Sprintf("Started pipeline %s in %s", pipeline, env)},
	}
	o.executions[exec.ID] = exec
	return exec
}

func (o *PipelineOrchestrator) AdvanceStage(execID string) error {
	o.mu.Lock()
	defer o.mu.Unlock()

	exec, ok := o.executions[execID]
	if !ok {
		return fmt.Errorf("execution %s not found", execID)
	}

	stages := o.pipelines[exec.Pipeline]
	currentIdx := -1
	for i, s := range stages {
		if s == exec.Stage {
			currentIdx = i
			break
		}
	}

	if currentIdx < 0 {
		return fmt.Errorf("stage %s not found in pipeline %s", exec.Stage, exec.Pipeline)
	}

	if currentIdx == len(stages)-1 {
		exec.Status = "success"
		now := time.Now()
		exec.FinishedAt = &now
		exec.DurationMs = now.Sub(exec.StartedAt).Milliseconds()
		exec.Logs = append(exec.Logs, "Pipeline completed successfully")

		// Update deployment record
		o.deployments[exec.Environment] = exec.ID
		return nil
	}

	nextStage := stages[currentIdx+1]
	exec.Stage = nextStage
	exec.Status = "running"
	exec.Logs = append(exec.Logs, fmt.Sprintf("Advanced to stage: %s", nextStage))
	return nil
}

func (o *PipelineOrchestrator) FailExecution(execID string, reason string) {
	o.mu.Lock()
	defer o.mu.Unlock()

	exec, ok := o.executions[execID]
	if !ok {
		return
	}
	exec.Status = "failed"
	now := time.Now()
	exec.FinishedAt = &now
	exec.DurationMs = now.Sub(exec.StartedAt).Milliseconds()
	exec.Logs = append(exec.Logs, fmt.Sprintf("Failed: %s", reason))
}

func (o *PipelineOrchestrator) GetExecution(execID string) (*PipelineExecution, bool) {
	o.mu.RLock()
	defer o.mu.RUnlock()
	exec, ok := o.executions[execID]
	return exec, ok
}

func (o *PipelineOrchestrator) GetAllExecutions() []*PipelineExecution {
	o.mu.RLock()
	defer o.mu.RUnlock()
	result := make([]*PipelineExecution, 0, len(o.executions))
	for _, e := range o.executions {
		result = append(result, e)
	}
	return result
}

func (o *PipelineOrchestrator) GetDeployments() map[string]string {
	o.mu.RLock()
	defer o.mu.RUnlock()
	result := make(map[string]string)
	for k, v := range o.deployments {
		result[k] = v
	}
	return result
}

func (o *PipelineOrchestrator) GetPipelineStatus(pipeline string) map[string]interface{} {
	o.mu.RLock()
	defer o.mu.RUnlock()

	var running, success, failed int
	for _, e := range o.executions {
		if e.Pipeline != pipeline {
			continue
		}
		switch e.Status {
		case "running":
			running++
		case "success":
			success++
		case "failed":
			failed++
		}
	}

	return map[string]interface{}{
		"pipeline":    pipeline,
		"running":     running,
		"success":     success,
		"failed":      failed,
		"deployments": o.deployments,
	}
}

func (o *PipelineOrchestrator) handleStart(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Pipeline string `json:"pipeline"`
		Env      string `json:"environment"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	exec := o.StartExecution(req.Pipeline, req.Env)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(exec)
}

func (o *PipelineOrchestrator) handleAdvance(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ExecutionID string `json:"execution_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := o.AdvanceStage(req.ExecutionID); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	exec, _ := o.GetExecution(req.ExecutionID)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(exec)
}

func (o *PipelineOrchestrator) handleFail(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ExecutionID string `json:"execution_id"`
		Reason      string `json:"reason"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	o.FailExecution(req.ExecutionID, req.Reason)
	exec, _ := o.GetExecution(req.ExecutionID)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(exec)
}

func (o *PipelineOrchestrator) handleStatus(w http.ResponseWriter, r *http.Request) {
	pipeline := r.URL.Query().Get("pipeline")
	if pipeline == "" {
		http.Error(w, "pipeline query param required", http.StatusBadRequest)
		return
	}

	status := o.GetPipelineStatus(pipeline)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

func (o *PipelineOrchestrator) handleExecutions(w http.ResponseWriter, r *http.Request) {
	executions := o.GetAllExecutions()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(executions)
}

func (o *PipelineOrchestrator) handleDeployments(w http.ResponseWriter, r *http.Request) {
	deployments := o.GetDeployments()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(deployments)
}

func main() {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	http.HandleFunc("/pipeline/start", orch.handleStart)
	http.HandleFunc("/pipeline/advance", orch.handleAdvance)
	http.HandleFunc("/pipeline/fail", orch.handleFail)
	http.HandleFunc("/pipeline/status", orch.handleStatus)
	http.HandleFunc("/executions", orch.handleExecutions)
	http.HandleFunc("/deployments", orch.handleDeployments)
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	log.Println("CI/CD Pipeline Orchestrator starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}