import React, { useCallback, useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Connection,
  Node,
  Edge,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { useStore } from '../store'
import { WorkflowNode, WorkflowEdge } from '../types'
import NodePalette from '../components/NodePalette'
import PropertiesPanel from '../components/PropertiesPanel'
import Toolbar from '../components/Toolbar'
import CustomNode from '../nodes/CustomNode'

const nodeTypes = { custom: CustomNode }

export default function App() {
  const { currentWorkflow, loadNodes, nodeDefs, addNode, updateNode, removeNode, addEdge: storeAddEdge, removeEdge, executeWorkflow, executionResult } = useStore()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  useEffect(() => {
    loadNodes()
  }, [loadNodes])

  useEffect(() => {
    if (currentWorkflow) {
      setNodes(currentWorkflow.nodes.map((n: WorkflowNode) => ({
        id: n.id,
        type: 'custom',
        position: n.position,
        data: { ...n, nodeDefs },
      })))
      setEdges(currentWorkflow.edges.map((e: WorkflowEdge) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        sourceHandle: e.sourceHandle,
        targetHandle: e.targetHandle,
        label: e.label,
      })))
    }
  }, [currentWorkflow, setNodes, setEdges, nodeDefs])

  const onConnect = useCallback(
    (params: Connection) => {
      const edge: WorkflowEdge = {
        id: `e_${Date.now()}`,
        source: params.source!,
        target: params.target!,
        sourceHandle: params.sourceHandle,
        targetHandle: params.targetHandle,
      }
      storeAddEdge(edge)
      setEdges((eds) => addEdge(edge, eds))
    },
    [storeAddEdge, setEdges],
  )

  const onNodeDragStop = useCallback(
    (event: React.MouseEvent, node: Node) => {
      updateNode(node.id, { position: node.position })
    },
    [updateNode],
  )

  const onNodesDelete = useCallback(
    (deleted: Node[]) => {
      deleted.forEach((n) => removeNode(n.id))
    },
    [removeNode],
  )

  const onEdgesDelete = useCallback(
    (deleted: Edge[]) => {
      deleted.forEach((e) => removeEdge(e.id))
    },
    [removeEdge],
  )

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const type = event.dataTransfer.getData('application/reactflow')
      const name = event.dataTransfer.getData('name')
      if (!type || !currentWorkflow) return
      const bounds = event.currentTarget.getBoundingClientRect()
      const position = {
        x: event.clientX - bounds.left - 75,
        y: event.clientY - bounds.top - 25,
      }
      addNode(type, name, position)
    },
    [addNode, currentWorkflow],
  )

  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Toolbar />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <NodePalette nodeDefs={nodeDefs} />
        <div
          style={{ flex: 1, position: 'relative' }}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={onNodeDragStop}
            onNodesDelete={onNodesDelete}
            onEdgesDelete={onEdgesDelete}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background color="#334155" gap={20} />
            <Controls />
            <MiniMap
              nodeColor={(n) => (n.data?.color || '#6366f1')}
              style={{ background: '#1e293b' }}
            />
          </ReactFlow>
        </div>
        <PropertiesPanel />
      </div>
      {executionResult && (
        <div
          style={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            background: '#1e293b',
            padding: 16,
            borderRadius: 8,
            maxWidth: 400,
            maxHeight: 300,
            overflow: 'auto',
            zIndex: 1000,
            border: '1px solid #334155',
          }}
        >
          <h4 style={{ marginBottom: 8 }}>Execution Result</h4>
          <pre style={{ fontSize: 12 }}>{JSON.stringify(executionResult, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
