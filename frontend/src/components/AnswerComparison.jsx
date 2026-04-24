import './AnswerComparison.css'

export default function AnswerComparison({ rag, nonRag }) {
  return (
    <div className="answer-grid">
      <AnswerCard
        title="RAG Answer"
        subtitle="With retrieved context"
        answer={rag}
        highlighted
      />
      <AnswerCard
        title="Direct Answer"
        subtitle="Without context"
        answer={nonRag}
      />
    </div>
  )
}

function AnswerCard({ title, subtitle, answer, highlighted }) {
  return (
    <div className={`answer-card ${highlighted ? 'answer-card--highlighted' : ''}`}>
      <div className="answer-card-header">
        <p className="answer-card-title">{title}</p>
        <p className="answer-card-subtitle">{subtitle}</p>
      </div>
      <p className="answer-card-text">{answer.text}</p>
      <div className="answer-card-meta">
        <span>{answer.latency_ms.toFixed(0)} ms</span>
        <span className="meta-dot">·</span>
        <span>${answer.cost_usd.toFixed(5)}</span>
      </div>
    </div>
  )
}
