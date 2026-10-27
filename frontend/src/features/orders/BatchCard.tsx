import type { ReactNode } from "react";
import { localTime, money } from "./api";
import type { Batch } from "./api";

export function BatchCard({
  batch,
  children,
}: {
  batch: Batch;
  children?: ReactNode;
}) {
  return (
    <article
      className="card order-batch"
      aria-label={`Batch ${batch.sequence} for ${batch.table_name}`}
    >
      <div className="order-batch-heading">
        <div>
          <h3>
            {batch.table_name} · Batch {batch.sequence}
          </h3>
          <p>
            {batch.submitted_by_name} · {localTime(batch.submitted_at)}
          </p>
        </div>
        <span className={`order-status order-${batch.status}`}>
          {batch.status}
        </span>
      </div>
      <ul className="order-lines">
        {batch.lines.map((line) => (
          <li key={line.id}>
            <div>
              <strong>
                {line.item_name} × {line.quantity}
              </strong>
              <small>{money(line.unit_price)} each</small>
            </div>
            <strong>{money(line.line_total)}</strong>
          </li>
        ))}
      </ul>
      <p className="order-total">
        <span>Batch total</span>
        <strong>{money(batch.total)}</strong>
      </p>
      {batch.reviewed_at && (
        <p className="order-meta">
          {batch.status === "approved" ? "Approved" : "Rejected"} by{" "}
          {batch.reviewed_by_name} · {localTime(batch.reviewed_at)}
        </p>
      )}
      {batch.rejection_reason && (
        <p className="order-reason">Reason: {batch.rejection_reason}</p>
      )}
      {children}
    </article>
  );
}
