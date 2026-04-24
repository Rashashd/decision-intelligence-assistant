import './PriorityPanel.css'

export default function PriorityPanel({ ml, llm }) {
  return (
    <div className="priority-panel">
      <p className="panel-label">Priority Assessment</p>
      <div className="priority-badges">
        <PriorityBadge source="ML Model" prediction={ml} />
        <PriorityBadge source="LLM" prediction={llm} />
      </div>
    </div>
  )
}

function PriorityBadge({ source, prediction }) {
  const urgent = prediction.label === 'urgent'
  return (
    <div className={`badge ${urgent ? 'badge--urgent' : 'badge--normal'}`}>
      <span className="badge-source">{source}</span>
      <span className="badge-label">{prediction.label}</span>
      <span className="badge-conf">{(prediction.confidence * 100).toFixed(0)}% confidence</span>
      <span className="badge-latency">{prediction.latency_ms.toFixed(0)} ms</span>
    </div>
  )
}
