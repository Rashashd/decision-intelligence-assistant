import './Recommendation.css'

export default function Recommendation({ ml, llm }) {
  const mlFaster = ml.latency_ms < llm.latency_ms
  const mlLatency = ml.latency_ms.toFixed(0)
  const llmLatency = llm.latency_ms.toFixed(0)
  const speedup = (llm.latency_ms / ml.latency_ms).toFixed(0)

  return (
    <div className="rec-wrap">
      <p className="rec-heading">Production recommendation</p>

      <div className="rec-verdict">
        <span className="rec-verdict-label">Deploy:</span>
        <span className="rec-verdict-value">ML Model</span>
      </div>

      <div className="rec-body">
        <p>
          For production priority classification, the <strong>ML model</strong> is the clear
          choice. It runs entirely on-device with <strong>no API cost</strong> and responds in{' '}
          <strong>{mlLatency} ms</strong> — roughly{' '}
          {mlFaster ? <><strong>{speedup}×</strong> faster</> : 'comparable'}
          {' '}than LLM zero-shot ({llmLatency} ms). At any meaningful request volume, the
          per-call cost of LLM inference compounds quickly; the ML model scales to thousands of
          tickets per second for free.
        </p>
        <p>
          <strong>LLM zero-shot</strong> is valuable as a <em>fallback</em> for edge-case tickets
          that fall outside the training distribution, or when you need a natural-language
          rationale alongside the prediction. RAG and non-RAG modes are better framed as{' '}
          <em>answer generators</em> for agent-facing responses rather than priority classifiers —
          they lack an explicit classification head and pay full LLM latency and cost on every
          call.
        </p>
        <p>
          <strong>Recommended architecture:</strong> route all incoming tickets through the ML
          model first. Flag low-confidence predictions (e.g. confidence &lt; 60%) for a secondary
          LLM zero-shot check. Use RAG only when a support agent requests a drafted response.
        </p>
      </div>
    </div>
  )
}
