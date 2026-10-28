import { useEffect, useState } from "react";
import { useAction } from "../../hooks/useAction";
import { kitchenApi } from "./api";
import type { KitchenTicket } from "./api";

export function ReadyItemsList() {
  const [tickets, setTickets] = useState<KitchenTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTickets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await kitchenApi.tickets("ready");
      setTickets(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load ready items.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const action = useAction();
  const handleServed = async (ticket: KitchenTicket) => {
    await action.run(async () => {
      await kitchenApi.markServed(ticket.order_line_id);
      await fetchTickets();
    });
  };

  return (
    <div className="card" style={{ marginBottom: "2rem", borderLeft: "4px solid var(--accent)" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Ready for Service</h2>
        <button className="btn btn-secondary" onClick={fetchTickets}>
          Refresh Ready Items
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
      {action.error && <div className="error-message">{action.error.message}</div>}

      <div style={{ marginTop: '1rem' }}>
        {loading ? (
          <div>Loading...</div>
        ) : tickets.length === 0 ? (
          <div className="empty-state">No items are ready.</div>
        ) : (
          <ul className="order-lines" style={{ padding: 0 }}>
            {tickets.map(ticket => (
              <li key={ticket.order_line_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                <div>
                  <strong>{ticket.quantity}x {ticket.item_name}</strong>
                  <div style={{ color: "var(--text-meta)", fontSize: "0.875rem" }}>
                    Table: {ticket.table_name} · Batch: {ticket.batch_sequence}
                  </div>
                </div>
                <button className="btn btn-primary" onClick={() => handleServed(ticket)}>
                  Mark Served
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
