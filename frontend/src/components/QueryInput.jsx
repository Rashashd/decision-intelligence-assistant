import './QueryInput.css'

export default function QueryInput({ onSubmit, loading }) {
  function handleSubmit(e) {
    e.preventDefault()
    const query = e.target.query.value.trim()
    if (query) onSubmit(query)
  }

  return (
    <form className="query-form" onSubmit={handleSubmit}>
      <div className="query-row">
        <input
          name="query"
          className="query-input"
          type="text"
          placeholder="Describe a customer support issue…"
          disabled={loading}
          autoComplete="off"
          autoFocus
        />
        <button className="query-btn" type="submit" disabled={loading}>
          {loading ? <span className="spinner" /> : 'Analyze'}
        </button>
      </div>
    </form>
  )
}
