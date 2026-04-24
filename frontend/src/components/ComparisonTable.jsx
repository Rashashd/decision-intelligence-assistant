import './ComparisonTable.css'

export default function ComparisonTable({ rag, nonRag, ml, llm }) {
  const rows = [
    {
      approach: 'RAG (LLM + context)',
      role: 'Answer generator',
      confidence: null,
      latency_ms: rag.latency_ms,
      cost_usd: rag.cost_usd,
    },
    {
      approach: 'Non-RAG (LLM only)',
      role: 'Answer generator',
      confidence: null,
      latency_ms: nonRag.latency_ms,
      cost_usd: nonRag.cost_usd,
    },
    {
      approach: 'ML Model',
      role: 'Priority classifier',
      confidence: ml.confidence,
      latency_ms: ml.latency_ms,
      cost_usd: ml.cost_usd,
    },
    {
      approach: 'LLM Zero-shot',
      role: 'Priority classifier',
      confidence: llm.confidence,
      latency_ms: llm.latency_ms,
      cost_usd: llm.cost_usd,
    },
  ]

  return (
    <div className="comparison-wrap">
      <p className="comparison-heading">Four-way comparison</p>
      <div className="comparison-table-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Approach</th>
              <th>Role</th>
              <th>Confidence</th>
              <th>Latency</th>
              <th>Cost / query</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.approach}>
                <td className="col-approach">{row.approach}</td>
                <td><span className={`role-chip ${row.role === 'Priority classifier' ? 'role-chip--classifier' : 'role-chip--generator'}`}>{row.role}</span></td>
                <td className="col-num">
                  {row.confidence != null
                    ? `${(row.confidence * 100).toFixed(0)}%`
                    : <span className="na">—</span>}
                </td>
                <td className="col-num">{row.latency_ms.toFixed(0)} ms</td>
                <td className="col-num">
                  {row.cost_usd === 0 ? <span className="free">$0.00</span> : `$${row.cost_usd.toFixed(5)}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
