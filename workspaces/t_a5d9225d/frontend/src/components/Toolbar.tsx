import React from 'react'
import { useStore } from '../store'
import * as api from '../services/api'

export default function Toolbar() {
  const { currentWorkflow, createWorkflow, executeWorkflow, loadWorkflows, deleteWorkflow } = useStore()
  const [name, setName] = React.useState('')

  const handleCreate = async () => {
    const n = name || 'Untitled Workflow'
    await createWorkflow(n)
    setName('')
    loadWorkflows()
  }

  const handleExport = async () => {
    if (!currentWorkflow) return
    const { code } = await api.exportWorkflow(currentWorkflow.id, 'python')
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentWorkflow.name}.py`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleDeploy = async () => {
    if (!currentWorkflow) return
    const result = await api.deployWorkflow(currentWorkflow.id, 'docker')
    alert(`Deployed: ${result.url}`)
  }

  const handleDelete = async () => {
    if (!currentWorkflow) return
    if (confirm(`Delete "${currentWorkflow.name}"?`)) {
      await deleteWorkflow(currentWorkflow.id)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', background: '#1e293b', borderBottom: '1px solid #334155' }}>
      <span style={{ fontWeight: 700, color: '#6366f1', marginRight: 16 }}>ChainForge</span>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="New workflow name..."
        style={{ padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 12 }}
      />
      <button onClick={handleCreate} style={btnStyle}>+ Create</button>
      <button onClick={executeWorkflow} style={{ ...btnStyle, background: '#10b981' }} disabled={!currentWorkflow}>
        Run
      </button>
      <button onClick={handleExport} style={btnStyle} disabled={!currentWorkflow}>
        Export
      </button>
      <button onClick={handleDeploy} style={{ ...btnStyle, background: '#8b5cf6' }} disabled={!currentWorkflow}>
        Deploy
      </button>
      <button onClick={handleDelete} style={{ ...btnStyle, background: '#ef4444' }} disabled={!currentWorkflow}>
        Delete
      </button>
      {currentWorkflow && (
        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#94a3b8' }}>
          {currentWorkflow.name} (v{currentWorkflow.version})
        </span>
      )}
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '4px 12px',
  borderRadius: 4,
  border: 'none',
  background: '#6366f1',
  color: '#fff',
  fontSize: 12,
  cursor: 'pointer',
}
