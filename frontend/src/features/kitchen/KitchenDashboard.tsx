import { useEffect, useState } from "react";
import { useAction } from "../../hooks/useAction";
import { kitchenApi } from "./api";
import type { KitchenTicket, KitchenStatus } from "./api";

function TicketCard({
  ticket,
  onAction
}: {
  ticket: KitchenTicket;
  onAction?: (action: 'preparing' | 'ready' | 'served', ticket: KitchenTicket) => void
}) {
  return (
    <div className="card" style={{ marginBottom: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <strong>{ticket.table_name}</strong>
        <span>Seq: {ticket.batch_sequence}</span>
      </div>
      <div style={{ fontSize: "1.25rem", margin: "0.5rem 0" }}>
        {ticket.quantity}x {ticket.item_name}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", color: "#666", fontSize: "0.875rem" }}>
        <span>Waiter: {ticket.waiter_name}</span>
        <span>{new Date(ticket.approved_at).toLocaleTimeString()}</span>
      </div>

      {onAction && (
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
          {ticket.status === "pending" && (
            <button className="btn btn-primary" onClick={() => onAction('preparing', ticket)}>
              Start Preparing
            </button>
          )}
          {ticket.status === "preparing" && (
            <button className="btn btn-primary" onClick={() => onAction('ready', ticket)}>
              Mark Ready
            </button>
          )}
          {ticket.status === "ready" && (
            <button className="btn btn-primary" onClick={() => onAction('served', ticket)}>
              Mark Served
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function KitchenDashboard() {
  const [filter, setFilter] = useState<KitchenStatus>("pending");
  const [tickets, setTickets] = useState<KitchenTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await kitchenApi.tickets(filter);
      setTickets(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tickets.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const action = useAction();

  const handleAction = async (actionType: 'preparing' | 'ready' | 'served', ticket: KitchenTicket) => {
    await action.run(async () => {
      if (actionType === 'preparing') {
        await kitchenApi.markPreparing(ticket.order_line_id);
      } else if (actionType === 'ready') {
        await kitchenApi.markReady(ticket.order_line_id);
      } else if (actionType === 'served') {
        await kitchenApi.markServed(ticket.order_line_id);
      }
      await fetchTickets();
    });
  };

  return (
    <div className="workspace-page">
      <header className="page-header">
        <h1>Kitchen Display System</h1>
        <div className="filters">
          {(["pending", "preparing", "ready", "served"] as KitchenStatus[]).map(status => (
            <button
              key={status}
              className={`btn ${filter === status ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(status)}
              style={{ marginRight: '0.5rem', textTransform: 'capitalize' }}
            >
              {status}
            </button>
          ))}
          <button className="btn btn-secondary" onClick={fetchTickets}>
            Refresh
          </button>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}
      {action.error && <div className="error-message">{action.error.message}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
        {loading ? (
          <div>Loading...</div>
        ) : tickets.length === 0 ? (
          <div className="empty-state">No {filter} items.</div>
        ) : (
          tickets.map(ticket => (
            <TicketCard
              key={ticket.order_line_id}
              ticket={ticket}
              onAction={
                (filter === "pending" || filter === "preparing")
                  ? handleAction
                  : undefined
              }
            />
          ))
        )}
      </div>
    </div>
  );
}
