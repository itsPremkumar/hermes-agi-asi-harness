import React from 'react'
import { Handle, Position, NodeProps } from 'reactflow'

export default function CustomNode({ data, selected }: NodeProps) {
  const color = data.color || '#6366f1'
  const status = data.status || 'idle'

  const statusColors: Record<string, string> = {
    idle: '#64748b',
    running: '#f59e0b',
    success: '#10b981',
    error: '#ef4444',
    skipped: '#6366f1',
  }

  return (
    <div
      style={{
        background: '#1e293b',
        border: `2px solid ${selected ? color : '#334155'}`,
        borderRadius: 8,
        padding: '8px 12px',
        minWidth: 140,
        color: '#e2e8f0',
        fontSize: 12,
        boxShadow: selected ? `0 0 10px ${color}40` : 'none',
      }}
    >
      {data.inputs?.map((port: any) => (
        <Handle
          key={port.id}
          type="target"
          position={Position.Left}
          id={port.id}
          style={{ background: color, width: 8, height: 8 }}
        />
      ))}
      {!data.inputs?.length && (
        <Handle type="target" position={Position.Left} style={{ background: color }} />
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: statusColors[status] || statusColors.idle,
          }}
        />
        <span style={{ fontWeight: 600, fontSize: 11 }}>{data.name}</span>
      </div>
      <div style={{ fontSize: 10, color: '#94a3b8' }}>{data.type}</div>
      {data.outputs?.map((port: any) => (
        <Handle
          key={port.id}
          type="source"
          position={Position.Right}
          id={port.id}
          style={{ background: color, width: 8, height: 8 }}
        />
      ))}
      {!data.outputs?.length && (
        <Handle type="source" position={Position.Right} style={{ background: color }} />
      )}
    </div>
  )
}
