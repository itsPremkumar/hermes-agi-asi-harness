export interface NodePort {
  id: string
  name: string
  type: string
  required?: boolean
}

export interface NodeDefinition {
  type: string
  name: string
  category: string
  description: string
  icon: string
  color: string
  inputs: NodePort[]
  outputs: NodePort[]
  config_schema: Record<string, any>
}

export interface Position {
  x: number
  y: number
}

export interface WorkflowNode {
  id: string
  type: string
  name: string
  position: Position
  data: Record<string, any>
  inputs: NodePort[]
  outputs: NodePort[]
  status?: string
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  label?: string | null
}

export interface Workflow {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  version: number
  tags: string[]
}
