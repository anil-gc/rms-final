import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth/auth-context";
import { ActionError, Button, Field, Notice } from "../../components/ui";
import { PageHeading, ResourceStatus } from "../../components/workspace-ui";
import { useAction } from "../../hooks/useAction";
import { useResource } from "../../hooks/useResource";
import { ApiError } from "../../lib/api";
import { workspace } from "../../lib/workspace";
import type { DiningTable, MenuItem } from "../../lib/workspace";
import { minorUnits, money, orderApi } from "./api";
import type { OrderDetail, Submission } from "./api";
import { BatchCard } from "./BatchCard";
import "./orders.css";
import { ReadyItemsList } from "../kitchen/ReadyItemsList";

function restoreAttempt(key: string): Submission | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || "null");
    if (
      value &&
      typeof value.idempotency_key === "string" &&
      Array.isArray(value.lines) &&
      value.lines.length > 0 &&
      value.lines.length <= 50 &&
      value.lines.every(
        (line: { menu_item: number; quantity: number }) =>
          line &&
          Number.isSafeInteger(line.menu_item) &&
          line.menu_item > 0 &&
          Number.isInteger(line.quantity) &&
          line.quantity >= 1 &&
          line.quantity <= 99,
      )
    )
      return value;
  } catch {
    /* Storage is optional; no unsafe request is automatically replayed. */
  }
  return null;
}

function Composer({
  order,
  saved,
  locked,
}: {
  order: OrderDetail;
  saved: () => Promise<void>;
  locked: (value: boolean) => void;
}) {
  const { user } = useAuth();
  const items = useResource(workspace.items);
  const categories = useResource(workspace.categories);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [cart, setCart] = useState<
    Record<number, { item: MenuItem; quantity: number }>
  >({});
  const storageKey = `rms:pending-order:${user?.id}:${order.id}`;
  const [attempt, setAttempt] = useState<Submission | null>(() =>
    restoreAttempt(storageKey),
  );
  const request = useRef<Submission | null>(attempt);
  const action = useAction();
  const [notice, setNotice] = useState("");
  const entries = Object.values(cart);
  const subtotal = entries.reduce(
    (sum, entry) => sum + minorUnits(entry.item.price) * BigInt(entry.quantity),
    0n,
  );
  const frozen = !!attempt || action.pending;
  useEffect(() => {
    locked(frozen);
    return () => locked(false);
  }, [frozen, locked]);
  useEffect(() => {
    if (!attempt) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [attempt]);
  function change(item: MenuItem, quantity: number) {
    if (frozen || !Number.isInteger(quantity) || quantity < 0 || quantity > 99)
      return;
    setNotice("");
    setCart((current) => {
      const next = { ...current };
      if (quantity === 0) delete next[item.id];
      else if (next[item.id] || Object.keys(next).length < 50)
        next[item.id] = { item, quantity };
      return next;
    });
  }
  async function submit() {
    if (!entries.length && !request.current) return;
    await action.run(async () => {
      const payload = request.current || {
        idempotency_key: crypto.randomUUID(),
        lines: entries.map((entry) => ({
          menu_item: entry.item.id,
          quantity: entry.quantity,
        })),
      };
      request.current = payload;
      setAttempt(payload);
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(payload));
      } catch {
        /* Memory fallback. */
      }
      let batch;
      try {
        batch = await orderApi.submit(order.id, payload);
      } catch (cause) {
        // Definite client rejection is safe to edit. A network/server failure is uncertain.
        if (
          cause instanceof ApiError &&
          cause.status >= 400 &&
          cause.status < 500
        ) {
          request.current = null;
          setAttempt(null);
          try {
            sessionStorage.removeItem(storageKey);
          } catch {
            /* Memory fallback. */
          }
        }
        throw cause;
      }
      request.current = null;
      setAttempt(null);
      setCart({});
      try {
        sessionStorage.removeItem(storageKey);
      } catch {
        /* Memory fallback. */
      }
      setNotice(
        `Batch ${batch.sequence} submitted. Total: ${money(batch.total)}.`,
      );
      await saved();
    });
  }
  const visible = (items.data || []).filter(
    (item) =>
      item.name.toLowerCase().includes(search.toLowerCase()) &&
      (!category || String(item.category) === category),
  );
  return (
    <section className="order-composer" aria-label="New order batch">
      <div className="order-batch-heading">
        <h2>Add a new batch</h2>
        <Button
          variant="secondary"
          disabled={frozen || items.loading || categories.loading}
          onClick={() => {
            void items.load();
            void categories.load();
          }}
        >
          Refresh menu
        </Button>
      </div>
      <p className="order-meta">
        New items need Cashier approval. Earlier batches stay unchanged. Up to
        50 different items, 99 of each.
      </p>
      {notice && <Notice kind="success">{notice}</Notice>}
      <ActionError error={action.error} remaining={action.remaining} />
      {attempt && !action.pending && (
        <Notice kind="info">
          This submission is unconfirmed. Retry the same batch to check its
          result safely before composing more items.
        </Notice>
      )}
      <ResourceStatus
        loading={items.loading || categories.loading}
        error={items.error || categories.error}
        retry={() => {
          void items.load();
          void categories.load();
        }}
      />
      <div className="order-menu-filters">
        <Field
          label="Search food"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="field">
          <label htmlFor="order-category">Category</label>
          <select
            id="order-category"
            className="input"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.data?.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {!items.loading && !items.error && !visible.length && (
        <p>No menu items match this view.</p>
      )}
      <div className="order-menu-grid">
        {!items.error &&
          visible.map((item) => (
            <article className="card order-menu-item" key={item.id}>
              <h3>{item.name}</h3>
              <p>{item.description}</p>
              <strong>{money(item.price)}</strong>
              <Button
                variant="secondary"
                disabled={
                  frozen ||
                  !item.effective_available ||
                  !!categories.error ||
                  (cart[item.id]?.quantity || 0) >= 99 ||
                  (!cart[item.id] && entries.length >= 50)
                }
                onClick={() => change(item, (cart[item.id]?.quantity || 0) + 1)}
              >
                {item.effective_available ? `Add ${item.name}` : "Unavailable"}
              </Button>
            </article>
          ))}
      </div>
      <div className="card order-cart">
        <h3>Review new items</h3>
        {!entries.length && !attempt && <p>Your new batch is empty.</p>}
        {entries.map(({ item, quantity }) => (
          <div className="order-cart-line" key={item.id}>
            <strong>{item.name}</strong>
            <Field
              label={`Quantity for ${item.name}`}
              type="number"
              min={1}
              max={99}
              step={1}
              value={quantity}
              disabled={frozen}
              onChange={(e) => {
                const value = e.target.valueAsNumber;
                if (Number.isInteger(value) && value >= 1 && value <= 99)
                  change(item, value);
                else
                  action.setError(
                    new ApiError("Use whole quantities from 1 to 99.", 400),
                  );
              }}
            />
            <span>{money(minorUnits(item.price) * BigInt(quantity))}</span>
            <Button
              variant="ghost"
              disabled={frozen}
              onClick={() => change(item, 0)}
            >
              Remove {item.name}
            </Button>
          </div>
        ))}
        {attempt && !entries.length && (
          <ul>
            {attempt.lines.map((line) => (
              <li key={line.menu_item}>
                Item #{line.menu_item} × {line.quantity} (unconfirmed
                submission)
              </li>
            ))}
          </ul>
        )}
        <p className="order-total">
          <span>Estimated subtotal</span>
          <strong>{money(subtotal)}</strong>
        </p>
        <p className="order-meta">
          Prices are checked by the server when submitted. This is not a bill.
        </p>
        <Button
          loading={action.pending}
          disabled={
            action.remaining > 0 ||
            (!entries.length && !attempt) ||
            (!attempt && (!!items.error || !!categories.error))
          }
          onClick={() => void submit()}
        >
          {attempt ? "Retry same batch" : "Submit for Cashier approval"}
        </Button>
      </div>
    </section>
  );
}

function TableOrder({
  table,
  onLock,
  changed,
}: {
  table: DiningTable;
  onLock: (value: boolean) => void;
  changed: () => Promise<void>;
}) {
  const loader = useCallback(() => orderApi.active(table.id), [table.id]);
  const resource = useResource(loader);
  const action = useAction();
  async function open() {
    await action.run(async () => {
      await orderApi.open(table.id);
      await Promise.all([resource.load(), changed()]);
    });
  }
  return (
    <section className="order-workspace" aria-label={`Order for ${table.name}`}>
      <div className="order-batch-heading">
        <h2>{table.name}</h2>
        <Button
          variant="secondary"
          onClick={() => void resource.load()}
          disabled={resource.loading}
        >
          Refresh order
        </Button>
      </div>
      <ResourceStatus
        loading={resource.loading && !resource.data}
        error={resource.error}
        retry={() => void resource.load()}
      />
      <ActionError error={action.error} remaining={action.remaining} />
      {!resource.error && resource.data === null && (
        <div className="card order-cart">
          <p>No active dining session.</p>
          {table.status === "occupied" ? (
            <Notice kind="info">
              This table was marked occupied manually. Ask your Owner or Manager
              to reconcile it before starting an order.
            </Notice>
          ) : (
            <Button
              loading={action.pending}
              disabled={!table.is_active || action.remaining > 0}
              onClick={() => void open()}
            >
              Start dining session
            </Button>
          )}
        </div>
      )}
      {!resource.error && resource.data && (
        <>
          <Notice kind="info">
            Dining session open. The table stays occupied until this visit is
            closed.
          </Notice>
          <div className="order-totals">
            {(["pending", "approved", "rejected"] as const).map((status) => (
              <span key={status}>
                {status}:{" "}
                <strong>{money(resource.data!.totals[status])}</strong>
              </span>
            ))}
          </div>
          <h2>Submitted batches</h2>
          {!resource.data.batches.length && <p>No batches submitted yet.</p>}
          <div className="order-batches">
            {resource.data.batches.map((batch) => (
              <BatchCard key={batch.id} batch={batch} />
            ))}
          </div>
          <Composer
            key={resource.data.id}
            order={resource.data}
            saved={resource.load}
            locked={onLock}
          />
        </>
      )}
    </section>
  );
}

export function WaiterOrdersPage() {
  const tables = useResource(workspace.tables);
  const [selected, setSelected] = useState<number | null>(null);
  const [locked, setLocked] = useState(false);
  const table = tables.data?.find((entry) => entry.id === selected);
  return (
    <div className="page-enter">
      <PageHeading
        eyebrow="TABLE SERVICE"
        title="Waiter orders"
        description="Choose a table, submit food, and follow Cashier approval."
      >
        <Button
          variant="secondary"
          disabled={locked || tables.loading}
          onClick={() => void tables.load()}
        >
          Refresh tables
        </Button>
      </PageHeading>
      <ResourceStatus
        loading={tables.loading && !tables.data}
        error={tables.error}
        retry={() => void tables.load()}
      />
      <ReadyItemsList />
      {!tables.loading && !tables.error && !tables.data?.length && (
        <Notice kind="info">
          No active tables. Ask management to configure tables first.
        </Notice>
      )}
      <div className="order-tables">
        {!tables.error &&
          tables.data?.map((entry) => (
            <button
              key={entry.id}
              type="button"
              className={`card order-table-choice ${selected === entry.id ? "order-selected" : ""}`}
              aria-label={`Select table ${entry.name} (${!entry.is_active ? "Unavailable" : entry.status === "available" ? "Available" : "Occupied"})`}
              aria-pressed={selected === entry.id}
              disabled={locked || !entry.is_active}
              onClick={() => setSelected(entry.id)}
            >
              <strong>{entry.name}</strong>
              <span>
                {!entry.is_active
                  ? "Unavailable"
                  : entry.status === "available"
                    ? "Available"
                    : "Occupied"}
              </span>
              <small>{entry.capacity} seats</small>
            </button>
          ))}
      </div>
      {table && !tables.error && (
        <TableOrder
          key={table.id}
          table={table}
          onLock={setLocked}
          changed={tables.load}
        />
      )}
    </div>
  );
}
