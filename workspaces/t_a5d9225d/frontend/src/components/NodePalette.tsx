import React from 'react'
import { NodeDefinition } from '../types'

interface Props {
  nodeDefs: Record<string, NodeDefinition[]>
}

export default function NodePalette({ nodeDefs }: Props) {
  const [search, setSearch] = React.useState('')

  const allNodes = Object.entries(nodeDefs).flatMap(([cat, nodes]) =>
    nodes.map((n) => ({ ...n, category: cat })),
  )
  const filtered = allNodes.filter(
    (n) =>
      !search ||
      n.name.toLowerCase().includes(search.toLowerCase()) ||
      n.type.toLowerCase().includes(search.toLowerCase()),
  )

  const onDragStart = (event: React.DragEvent, def: NodeDefinition) => {
    event.dataTransfer.setData('application/reactflow', def.type)
    event.dataTransfer.setData('name', def.name)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div style={{ width: 220, background: '#1e293b', borderRight: '1px solid #334155', overflow: 'auto', padding: 12 }}>
      <h3 style={{ fontSize: 13, marginBottom: 8, color: '#94a3b8' }}>Nodes</h3>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search..."
        style={{ width: '100%', padding: '4px 8px', borderRadius: 4, border: '1px solid #334155', background: '#0f172a', color: '#e2e8f0', fontSize: 11, marginBottom: 8 }}
      />
      {Object.entries(nodeDefs).map(([cat, nodes]) => {
        const shown = filtered.filter((n) => n.category === cat)
        if (!shown.length) return null
        return (
          <div key={cat} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', marginBottom: 4 }}>{cat}</div>
            {shown.map((def) => (
              <div
                key={def.type}
                draggable
                onDragStart={(e) => onDragStart(e, def)}
                style={{
                  padding: '6px 8px',
                  marginBottom: 4,
                  borderRadius: 4,
                  background: '#0f172a',
                  border: '1px solid #334155',
                  cursor: 'grab',
                  fontSize: 11,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: def.color }} />
                <span>{def.name}</span>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
