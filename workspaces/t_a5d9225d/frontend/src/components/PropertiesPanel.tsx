import React from 'react'
import { useStore } from '../store'

export default function PropertiesPanel() {
  const { selectedNode, updateNode } = useStore()

  if (!selectedNode) {
    return (
      <div style={{ width: 250, background: '#1e293b', borderLeft: '1px solid #334155', padding: 16, fontSize: 12, color: '#64748b' }}>
        <p>Select a node to edit its properties.</p>
      </div>
    )
  }

  const handleChange = (key: string, value: any) => {
    updateNode(selectedNode.id, { data: { ...selectedNode.data, [key]: value } })
  }

  return (
    <div style={{ width: 250, background: '#1e293b', borderLeft: '1px solid #334155', overflow: 'auto', padding: 16, fontSize: 12 }}>
      <h3 style={{ fontSize: 13, marginBottom: 12 }}>Properties</h3>
      <div style={{ marginBottom: 8 }}>
        <label style={{ color: '#94a3b8', display: 'block', marginBottom: 2 }}>Name</label>
        <input
          value={selectedNode.name}
          onChange={(e) => updateNode(selectedNode.id, { name: e.target.value })}
          style={{ width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0' }}
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={{ color: '#94a3b8', display: 'block', marginBottom: 2 }}>Type</label>
        <div style={{ color: '#e2e8f0' }}>{selectedNode.type}</div>
      </div>
      <div style={{ marginBottom: 8 }}>
        <label style={{ color: '#94a3b8', display: 'block', marginBottom: 2 }}>ID</label>
        <div style={{ color: '#64748b', fontSize: 10 }}>{selectedNode.id}</div>
      </div>
      {selectedNode.data && Object.keys(selectedNode.data).length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h4 style={{ fontSize: 12, marginBottom: 8, color: '#94a3b8' }}>Data</h4>
          {Object.entries(selectedNode.data).map(([key, value]) => (
            <div key={key} style={{ marginBottom: 8 }}>
              <label style={{ color: '#94a3b8', display: 'block', marginBottom: 2 }}>{key}</label>
              <input
                value={String(value)}
                onChange={(e) => handleChange(key, e.target.value)}
                style={{ width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0' }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
