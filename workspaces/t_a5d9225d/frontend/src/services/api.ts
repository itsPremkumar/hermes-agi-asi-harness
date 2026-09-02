import axios from 'axios'
import { NodeDefinition, Workflow, WorkflowExecution } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

export async function fetchNodes(): Promise<Record<string, NodeDefinition[]>> {
  const { data } = await api.get('/nodes')
  return data
}

export async function fetchNode(type: string): Promise<NodeDefinition> {
  const { data } = await api.get(`/nodes/${type}`)
  return data
}

export async function createWorkflow(name: string): Promise<Workflow> {
  const { data } = await api.post('/workflows', { name })
  return data
}

export async function fetchWorkflows(): Promise<Workflow[]> {
  const { data } = await api.get('/workflows')
  return data
}

export async function fetchWorkflow(id: string): Promise<Workflow> {
  const { data } = await api.get(`/workflows/${id}`)
  return data
}

export async function updateWorkflow(id: string, body: Record<string, any>): Promise<Workflow> {
  const { data } = await api.put(`/workflows/${id}`, body)
  return data
}

export async function deleteWorkflow(id: string): Promise<void> {
  await api.delete(`/workflows/${id}`)
}

export async function executeWorkflow(id: string): Promise<WorkflowExecution> {
  const { data } = await api.post(`/workflows/${id}/execute`)
  return data
}

export async function exportWorkflow(id: string, format: string): Promise<{ code: string }> {
  const { data } = await api.post('/export', { workflow_id: id, format })
  return data
}

export async function deployWorkflow(id: string, target: string): Promise<any> {
  const { data } = await api.post('/deploy', { workflow_id: id, target })
  return data
}
