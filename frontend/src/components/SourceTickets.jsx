import './SourceTickets.css'

export default function SourceTickets({ tickets }) {
  return (
    <div className="sources">
      <p className="panel-label">
        Retrieved Sources
        <span className="sources-count">{tickets.length}</span>
      </p>
      <div className="sources-list">
        {tickets.map((ticket, i) => (
          <TicketCard key={i} ticket={ticket} />
        ))}
      </div>
    </div>
  )
}

function TicketCard({ ticket }) {
  const pct = (ticket.similarity_score * 100).toFixed(0)
  return (
    <div className="ticket-card">
      <div className="ticket-card-header">
        <span className="ticket-brand">{ticket.brand ?? 'Unknown'}</span>
        <span className="ticket-score">{pct}% match</span>
      </div>
      <p className="ticket-text">{ticket.text}</p>
      {ticket.company_reply && (
        <div className="ticket-reply">
          <span className="ticket-reply-label">Company reply</span>
          <p className="ticket-reply-text">{ticket.company_reply}</p>
        </div>
      )}
    </div>
  )
}
