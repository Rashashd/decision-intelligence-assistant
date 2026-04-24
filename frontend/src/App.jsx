import { useState } from 'react'
import { submitQuery } from './api/query'
import QueryInput from './components/QueryInput'
import PriorityPanel from './components/PriorityPanel'
import AnswerComparison from './components/AnswerComparison'
import SourceTickets from './components/SourceTickets'
import ComparisonTable from './components/ComparisonTable'
import Recommendation from './components/Recommendation'
import './App.css'

export default function App() {
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  async function handleQuery(query) {
    setLoading(true)
    setError(null)
    try {
      setResult(await submitQuery(query))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <span className="app-logo">DIA</span>
          <span className="app-name">Decision Intelligence Assistant</span>
        </div>
      </header>

      <main className="app-main">
        <div className="app-content">
          {!result && !loading && (
            <div className="hero">
              <h1 className="hero-title">Analyze customer support issues</h1>
              <p className="hero-sub">
                Get RAG-powered answers, priority predictions, and similar ticket references.
              </p>
            </div>
          )}

          <QueryInput onSubmit={handleQuery} loading={loading} />

          {error && <p className="error-msg">{error}</p>}

          {result && (
            <div className="results">
              <PriorityPanel ml={result.ml_priority} llm={result.llm_priority} />
              <AnswerComparison rag={result.rag_answer} nonRag={result.non_rag_answer} />
              <ComparisonTable
                rag={result.rag_answer}
                nonRag={result.non_rag_answer}
                ml={result.ml_priority}
                llm={result.llm_priority}
              />
              <Recommendation ml={result.ml_priority} llm={result.llm_priority} />
              <SourceTickets tickets={result.retrieved_tickets} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
