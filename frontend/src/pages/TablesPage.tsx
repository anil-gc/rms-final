import { useState } from "react";
import type { FormEvent } from "react";
import { Armchair, Pencil, Plus, Search, UsersRound } from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { ActionError, Button, Dialog, Field, Notice } from "../components/ui";
import {
  EmptyRecords,
  PageHeading,
  ReadOnlyNote,
  RecordBadge,
  ResourceStatus,
  SetupNotice,
  Toggle,
} from "../components/workspace-ui";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { canManageWorkspace, workspace } from "../lib/workspace";
import type { DiningTable, TableInput } from "../lib/workspace";

function TableDialog({
  table,
  close,
  saved,
}: {
  table?: DiningTable;
  close: () => void;
  saved: () => void;
}) {
  const [form, setForm] = useState<TableInput>({
    name: table?.name || "",
    capacity: table?.capacity || 2,
    status: table?.status || "available",
    is_active: table?.is_active ?? true,
  });
  const action = useAction();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await action.run(() => workspace.saveTable(form, table?.id))) saved();
  }
  return (
    <Dialog
      title={table ? "Edit table" : "Add table"}
      onClose={close}
      busy={action.pending}
    >
      <form className="dialog-body form-stack" onSubmit={submit}>
        <ActionError error={action.error} remaining={action.remaining} />
        <Field
          label="Table name"
          required
          maxLength={40}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          error={action.error?.fields.name}
          placeholder="e.g. T01 or Garden 1"
        />
        <Field
          label="Seats"
          type="number"
          required
          min={1}
          max={50}
          step={1}
          value={form.capacity}
          onChange={(e) =>
            setForm({ ...form, capacity: Number(e.target.value) })
          }
          error={action.error?.fields.capacity}
        />
        <div className="field">
          <label htmlFor="table-status">Occupancy</label>
          <select
            id="table-status"
            className="input"
            disabled={table?.has_active_session}
            value={form.status}
            aria-describedby={
              action.error?.fields.status ? "table-status-error" : undefined
            }
            aria-invalid={!!action.error?.fields.status || undefined}
            onChange={(e) =>
              setForm({
                ...form,
                status: e.target.value as DiningTable["status"],
              })
            }
          >
            <option value="available">Available</option>
            <option value="occupied">Occupied</option>
          </select>
          {action.error?.fields.status && (
            <span id="table-status-error" className="field-error">
              {action.error.fields.status}
            </span>
          )}
          <span className="field-hint">
            {table?.has_active_session
              ? "An active dining session keeps this table occupied until the visit is closed."
              : "Updated manually by your Owner or Manager."}
          </span>
        </div>
        <Toggle
          label="Table active"
          checked={form.is_active}
          disabled={table?.has_active_session}
          onChange={(value) => setForm({ ...form, is_active: value })}
          hint="Mark a table available before archiving it. Archived tables are hidden from staff."
        />
        <div className="dialog-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={close}
            disabled={action.pending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={action.pending}
            disabled={action.remaining > 0}
          >
            Save table
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export function TablesPage() {
  const { user } = useAuth();
  const editable = canManageWorkspace(user?.role);
  const profile = useResource(workspace.restaurant);
  const tables = useResource(workspace.tables);
  const [editor, setEditor] = useState<{ table?: DiningTable } | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("active");
  const [notice, setNotice] = useState("");
  const failed = profile.error || tables.error;
  const loading =
    (tables.loading && !tables.data) ||
    (profile.loading && profile.data === undefined);
  const filtered = (tables.data || []).filter(
    (table) =>
      table.name.toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" ||
        (filter === "active"
          ? table.is_active
          : filter === "archived"
            ? !table.is_active
            : table.is_active && table.status === filter)),
  );
  function refresh() {
    void tables.load();
    void profile.load();
  }
  function open(table?: DiningTable) {
    setNotice("");
    setEditor({ table });
  }
  return (
    <div className="page-enter">
      <PageHeading
        eyebrow="A PLACE FOR EVERY GUEST"
        title="Tables"
        description="Keep your table names, seating, and current occupancy organised."
      >
        {editable && (
          <Button onClick={() => open()} disabled={!profile.data || !!failed}>
            <Plus size={17} />
            Add table
          </Button>
        )}
      </PageHeading>
      {!editable && <ReadOnlyNote />}
      {notice && (
        <div className="mb-6">
          <Notice kind="success">{notice}</Notice>
        </div>
      )}
      <ResourceStatus loading={!!loading} error={failed} retry={refresh} />
      {profile.data === null && !failed && <SetupNotice />}
      {profile.data && !failed && !loading && (
        <>
          <div className="table-summary-grid">
            <div className="card table-stat">
              <span>
                <Armchair size={18} />
                Active tables
              </span>
              <strong>
                {tables.data?.filter((table) => table.is_active).length}
              </strong>
            </div>
            <div className="card table-stat">
              <span>
                <span className="tiny-dot" />
                Available
              </span>
              <strong>
                {
                  tables.data?.filter(
                    (table) => table.is_active && table.status === "available",
                  ).length
                }
              </strong>
            </div>
            <div className="card table-stat">
              <span>
                <UsersRound size={18} />
                Occupied
              </span>
              <strong>
                {
                  tables.data?.filter(
                    (table) => table.is_active && table.status === "occupied",
                  ).length
                }
              </strong>
            </div>
          </div>
          <div className="card catalogue-toolbar">
            <div className="search-input">
              <Search size={18} />
              <input
                aria-label="Search tables"
                placeholder="Find a table…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <select
              className="input filter-select"
              aria-label="Filter tables"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="active">Active tables</option>
              <option value="available">Available</option>
              <option value="occupied">Occupied</option>
              {editable && (
                <>
                  <option value="archived">Archived tables</option>
                  <option value="all">All tables</option>
                </>
              )}
            </select>
          </div>
          {filtered.length ? (
            <div className="dining-table-grid">
              {filtered.map((table) => (
                <article
                  className={`card dining-table-card ${table.status === "occupied" && table.is_active ? "table-occupied" : ""}`}
                  key={table.id}
                >
                  <div className="dining-table-top">
                    <RecordBadge
                      active={table.is_active && table.status === "available"}
                    >
                      {!table.is_active
                        ? "Archived"
                        : table.status === "available"
                          ? "Available"
                          : "Occupied"}
                    </RecordBadge>
                    {editable && (
                      <button
                        className="icon-button"
                        aria-label={`Edit table ${table.name}`}
                        onClick={() => open(table)}
                      >
                        <Pencil size={16} />
                      </button>
                    )}
                  </div>
                  <div className="table-illustration" aria-hidden="true">
                    <span />
                    <div>
                      <Armchair size={27} strokeWidth={1.5} />
                    </div>
                    <span />
                  </div>
                  <h2>{table.name}</h2>
                  <p>
                    <UsersRound size={15} />
                    {table.capacity} seats
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <div className="card">
              <EmptyRecords
                title={
                  tables.data?.length
                    ? "No tables match this view."
                    : "Set the scene for your guests."
                }
                description={
                  tables.data?.length
                    ? "Try a different name or occupancy filter."
                    : "Add your tables with clear names and seating capacity."
                }
                action={
                  editable && !tables.data?.length
                    ? "Add your first table"
                    : undefined
                }
                onAction={() => open()}
              />
            </div>
          )}
          <p className="workspace-note">
            <Armchair size={17} />
            Dining sessions keep tables occupied. Manual occupancy changes are
            available to your Owner or Manager when no active session exists.
          </p>
        </>
      )}
      {editor && (
        <TableDialog
          table={editor.table}
          close={() => setEditor(null)}
          saved={() => {
            setEditor(null);
            setNotice("Table saved.");
            refresh();
          }}
        />
      )}
    </div>
  );
}
