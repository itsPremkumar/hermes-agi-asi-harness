package main

import (
	"testing"
	"time"
)

func TestPipelineOrchestrator_StartExecution(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")
	if exec.Pipeline != "default" {
		t.Errorf("StartExecution() pipeline = %s, want default", exec.Pipeline)
	}
	if exec.Status != "running" {
		t.Errorf("StartExecution() status = %s, want running", exec.Status)
	}
	if exec.Environment != "staging" {
		t.Errorf("StartExecution() env = %s, want staging", exec.Environment)
	}
	if len(exec.Logs) == 0 {
		t.Error("expected logs to be non-empty")
	}
}

func TestPipelineOrchestrator_AdvanceStage(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")

	// Advance through all stages
	for i := 0; i < 4; i++ {
		err := orch.AdvanceStage(exec.ID)
		if err != nil {
			t.Fatalf("AdvanceStage() error = %v", err)
		}
	}

	// Final stage should be success
	updated, _ := orch.GetExecution(exec.ID)
	if updated.Status != "success" {
		t.Errorf("expected status=success, got %s", updated.Status)
	}
	if updated.FinishedAt == nil {
		t.Error("expected FinishedAt to be set")
	}
	if updated.DurationMs <= 0 {
		t.Errorf("expected DurationMs > 0, got %d", updated.DurationMs)
	}
}

func TestPipelineOrchestrator_FailExecution(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "production")
	orch.FailExecution(exec.ID, "test failure")

	updated, _ := orch.GetExecution(exec.ID)
	if updated.Status != "failed" {
		t.Errorf("expected status=failed, got %s", updated.Status)
	}
	if updated.FinishedAt == nil {
		t.Error("expected FinishedAt to be set")
	}
	found := false
	for _, log := range updated.Logs {
		if log == "Failed: test failure" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected failure log entry")
	}
}

func TestPipelineOrchestrator_GetExecution(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")
	retrieved, ok := orch.GetExecution(exec.ID)
	if !ok {
		t.Error("GetExecution() ok = false, want true")
	}
	if retrieved.ID != exec.ID {
		t.Errorf("GetExecution() ID = %s, want %s", retrieved.ID, exec.ID)
	}

	_, ok = orch.GetExecution("nonexistent")
	if ok {
		t.Error("GetExecution() ok = true for nonexistent, want false")
	}
}

func TestPipelineOrchestrator_GetAllExecutions(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	for i := 0; i < 5; i++ {
		orch.StartExecution("default", "staging")
	}

	executions := orch.GetAllExecutions()
	if len(executions) != 5 {
		t.Errorf("GetAllExecutions() length = %d, want 5", len(executions))
	}
}

func TestPipelineOrchestrator_GetPipelineStatus(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	// Start some executions
	for i := 0; i < 3; i++ {
		exec := orch.StartExecution("default", "staging")
		if i%2 == 0 {
			orch.AdvanceStage(exec.ID)
		} else {
			orch.FailExecution(exec.ID, "test")
		}
	}

	status := orch.GetPipelineStatus("default")
	if status["pipeline"] != "default" {
		t.Errorf("GetPipelineStatus() pipeline = %s, want default", status["pipeline"])
	}

	running, ok := status["running"].(int)
	if !ok {
		t.Error("GetPipelineStatus() running not int")
	}
	success, ok := status["success"].(int)
	if !ok {
		t.Error("GetPipelineStatus() success not int")
	}
	failed, ok := status["failed"].(int)
	if !ok {
		t.Error("GetPipelineStatus() failed not int")
	}

	if running+success+failed != 3 {
		t.Errorf("total executions = %d, want 3", running+success+failed)
	}
}

func TestPipelineOrchestrator_GetDeployments(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "production")
	orch.AdvanceStage(exec.ID)
	orch.AdvanceStage(exec.ID)
	orch.AdvanceStage(exec.ID)
	orch.AdvanceStage(exec.ID)

	deployments := orch.GetDeployments()
	if len(deployments) == 0 {
		t.Error("GetDeployments() empty, want non-empty")
	}
	if _, ok := deployments["production"]; !ok {
		t.Error("GetDeployments() missing production entry")
	}
}

func TestPipelineOrchestrator_MultiplePipelines(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("pipeline-A", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})
	orch.RegisterPipeline("pipeline-B", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	execA := orch.StartExecution("pipeline-A", "staging")
	execB := orch.StartExecution("pipeline-B", "production")

	orch.AdvanceStage(execA.ID)
	orch.AdvanceStage(execB.ID)

	statusA := orch.GetPipelineStatus("pipeline-A")
	statusB := orch.GetPipelineStatus("pipeline-B")

	runningA := statusA["running"].(int)
	runningB := statusB["running"].(int)

	if runningA+runningA != 1 {
		t.Errorf("pipeline-A running = %d, want 1", runningA)
	}
	if runningB+runningB != 1 {
		t.Errorf("pipeline-B running = %d, want 1", runningB)
	}
}

func TestPipelineOrchestrator_UnknownPipeline(t *testing.T) {
	orch := NewPipelineOrchestrator()

	exec := orch.StartExecution("unknown", "staging")
	err := orch.AdvanceStage(exec.ID)
	if err == nil {
		t.Error("expected error for unknown pipeline stage")
	}
}

func TestPipelineOrchestrator_AlreadyCompleted(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")
	for i := 0; i < 4; i++ {
		orch.AdvanceStage(exec.ID)
	}

	// Try advancing completed pipeline
	err := orch.AdvanceStage(exec.ID)
	if err == nil {
		t.Error("expected error for already completed pipeline")
	}
}

func TestPipelineOrchestrator_NonExistentExecution(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	err := orch.AdvanceStage("nonexistent-id")
	if err == nil {
		t.Error("expected error for nonexistent execution")
	}
}

func TestPipelineOrchestrator_ConcurrentExecutions(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	done := make(chan bool, 10)
	for i := 0; i < 10; i++ {
		go func(idx int) {
			exec := orch.StartExecution("default", "staging")
			orch.AdvanceStage(exec.ID)
			done <- true
		}(i)
	}

	for i := 0; i < 10; i++ {
		<-done
	}

	executions := orch.GetAllExecutions()
	if len(executions) != 10 {
		t.Errorf("GetAllExecutions() length = %d, want 10", len(executions))
	}
}

func TestPipelineOrchestrator_HTTPStart(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	req := struct {
		Pipeline string `json:"pipeline"`
		Env      string `json:"environment"`
	}{Pipeline: "default", Env: "staging"}
	body, _ := json.Marshal(req)

	// Test via HTTP handler
	httpReq, _ := http.NewRequest(http.MethodPost, "/pipeline/start", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleStart(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleStart() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var exec PipelineExecution
	json.NewDecoder(rr.Body).Decode(&exec)
	if exec.Pipeline != "default" {
		t.Errorf("handleStart() pipeline = %s, want default", exec.Pipeline)
	}
}

func TestPipelineOrchestrator_HTTPAdvance(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")

	req := struct {
		ExecutionID string `json:"execution_id"`
	}{ExecutionID: exec.ID}
	body, _ := json.Marshal(req)

	httpReq, _ := http.NewRequest(http.MethodPost, "/pipeline/advance", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleAdvance(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleAdvance() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var updated PipelineExecution
	json.NewDecoder(rr.Body).Decode(&updated)
	if updated.Stage != StageBuild {
		t.Errorf("handleAdvance() stage = %s, want %s", updated.Stage, StageBuild)
	}
}

func TestPipelineOrchestrator_HTTPFail(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")

	req := struct {
		ExecutionID string `json:"execution_id"`
		Reason      string `json:"reason"`
	}{ExecutionID: exec.ID, Reason: "test failure"}
	body, _ := json.Marshal(req)

	httpReq, _ := http.NewRequest(http.MethodPost, "/pipeline/fail", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleFail(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleFail() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var updated PipelineExecution
	json.NewDecoder(rr.Body).Decode(&updated)
	if updated.Status != "failed" {
		t.Errorf("handleFail() status = %s, want failed", updated.Status)
	}
}

func TestPipelineOrchestrator_HTTPStatus(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "staging")
	orch.AdvanceStage(exec.ID)

	httpReq, _ := http.NewRequest(http.MethodGet, "/pipeline/status?pipeline=default", nil)
	rr := httptest.NewRecorder()

	orch.handleStatus(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleStatus() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var status map[string]interface{}
	json.NewDecoder(rr.Body).Decode(&status)
	if status["pipeline"] != "default" {
		t.Errorf("handleStatus() pipeline = %s, want default", status["pipeline"])
	}
}

func TestPipelineOrchestrator_HTTPExecutions(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	for i := 0; i < 3; i++ {
		orch.StartExecution("default", "staging")
	}

	httpReq, _ := http.NewRequest(http.MethodGet, "/executions", nil)
	rr := httptest.NewRecorder()

	orch.handleExecutions(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleExecutions() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var executions []*PipelineExecution
	json.NewDecoder(rr.Body).Decode(&executions)
	if len(executions) != 3 {
		t.Errorf("handleExecutions() length = %d, want 3", len(executions))
	}
}

func TestPipelineOrchestrator_HTTPDeployments(t *testing.T) {
	orch := NewPipelineOrchestrator()
	orch.RegisterPipeline("default", []PipelineStage{StageTest, StageBuild, StageDeploy, StageMonitor})

	exec := orch.StartExecution("default", "production")
	for i := 0; i < 4; i++ {
		orch.AdvanceStage(exec.ID)
	}

	httpReq, _ := http.NewRequest(http.MethodGet, "/deployments", nil)
	rr := httptest.NewRecorder()

	orch.handleDeployments(rr, httpReq)

	if rr.Code != http.StatusOK {
		t.Errorf("handleDeployments() status = %d, want %d", rr.Code, http.StatusOK)
	}

	var deployments map[string]string
	json.NewDecoder(rr.Body).Decode(&deployments)
	if _, ok := deployments["production"]; !ok {
		t.Error("handleDeployments() missing production")
	}
}

func TestPipelineOrchestrator_HandleStartInvalidJSON(t *testing.T) {
	orch := NewPipelineOrchestrator()
	req := httptest.NewRequest(http.MethodPost, "/pipeline/start", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleStart(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("handleStart() status = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestPipelineOrchestrator_HandleAdvanceInvalidJSON(t *testing.T) {
	orch := NewPipelineOrchestrator()
	req := httptest.NewRequest(http.MethodPost, "/pipeline/advance", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleAdvance(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("handleAdvance() status = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestPipelineOrchestrator_HandleFailInvalidJSON(t *testing.T) {
	orch := NewPipelineOrchestrator()
	req := httptest.NewRequest(http.MethodPost, "/pipeline/fail", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	orch.handleFail(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("handleFail() status = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestPipelineOrchestrator_HandleStatusMissingParam(t *testing.T) {
	orch := NewPipelineOrchestrator()
	httpReq, _ := http.NewRequest(http.MethodGet, "/pipeline/status", nil)
	rr := httptest.NewRecorder()

	orch.handleStatus(rr, httpReq)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("handleStatus() status = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}