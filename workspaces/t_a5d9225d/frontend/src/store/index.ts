import { create } from 'zustand'
import { Workflow, WorkflowNode, WorkflowEdge, NodeDefinition } from '../types'
import * as api from '../services/api'

interface ChainForgeState {
  workflows: Workflow[]
  currentWorkflow: Workflow | null
  nodeDefs: Record<string, NodeDefinition[]>
  selectedNode: WorkflowNode | null
  executionResult: any

  loadNodes: () => Promise<void>
  loadWorkflows: () => Promise<void>
  selectWorkflow: (id: string) => Promise<void>
  createWorkflow: (name: string) => Promise<void>
  updateWorkflow: (id: string, body: Record<string, any>) => Promise<void>
  deleteWorkflow: (id: string) => Promise<void>
  addNode: (type: string, name: string, position: { x: number; y: number }) => void
  updateNode: (id: string, body: Record<string, any>) => void
  removeNode: (id: string) => void
  addEdge: (edge: WorkflowEdge) => void
  removeEdge: (id: string) => void
  setSelectedNode: (node: WorkflowNode | null) => void
  executeWorkflow: () => Promise<void>
}

export const useStore = create<ChainForgeState>((set, get) => ({
  workflows: [],
  currentWorkflow: null,
  nodeDefs: {},
  selectedNode: null,
  executionResult: null,

  loadNodes: async () => {
    const nodeDefs = await api.fetchNodes()
    set({ nodeDefs })
  },

  loadWorkflows: async () => {
    const workflows = await api.fetchWorkflows()
    set({ workflows })
  },

  selectWorkflow: async (id: string) => {
    const wf = await api.fetchWorkflow(id)
    set({ currentWorkflow: wf })
  },

  createWorkflow: async (name: string) => {
    const wf = await api.createWorkflow(name)
    set((s) => ({ workflows: [...s.workflows, wf], currentWorkflow: wf }))
  },

  updateWorkflow: async (id: string, body: Record<string, any>) => {
    const wf = await api.updateWorkflow(id, body)
    set((s) => ({
      workflows: s.workflows.map((w) => (w.id === id ? wf : w)),
      currentWorkflow: s.currentWorkflow?.id === id ? wf : s.currentWorkflow,
    }))
  },

  deleteWorkflow: async (id: string) => {
    await api.deleteWorkflow(id)
    set((s) => ({
      workflows: s.workflows.filter((w) => w.id !== id),
      currentWorkflow: s.currentWorkflow?.id === id ? null : s.currentWorkflow,
    }))
  },

  addNode: (type: string, name: string, position: { x: number; y: number }) => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const id = `n_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    const node: WorkflowNode = {
      id,
      type,
      name,
      position,
      data: {},
      inputs: [],
      outputs: [],
    }
    const wf = { ...currentWorkflow, nodes: [...currentWorkflow.nodes, node] }
    set({ currentWorkflow: wf })
  },

  updateNode: (id: string, body: Record<string, any>) => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const nodes = currentWorkflow.nodes.map((n) =>
      n.id === id ? { ...n, ...body } : n,
    )
    set({ currentWorkflow: { ...currentWorkflow, nodes } })
  },

  removeNode: (id: string) => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const nodes = currentWorkflow.nodes.filter((n) => n.id !== id)
    const edges = currentWorkflow.edges.filter((e) => e.source !== id && e.target !== id)
    set({ currentWorkflow: { ...currentWorkflow, nodes, edges } })
  },

  addEdge: (edge: WorkflowEdge) => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const edges = [...currentWorkflow.edges, edge]
    set({ currentWorkflow: { ...currentWorkflow, edges } })
  },

  removeEdge: (id: string) => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const edges = currentWorkflow.edges.filter((e) => e.id !== id)
    set({ currentWorkflow: { ...currentWorkflow, edges } })
  },

  setSelectedNode: (node: WorkflowNode | null) => set({ selectedNode: node }),

  executeWorkflow: async () => {
    const { currentWorkflow } = get()
    if (!currentWorkflow) return
    const result = await api.executeWorkflow(currentWorkflow.id)
    set({ executionResult: result })
  },
}))
