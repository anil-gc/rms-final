import { workspaceRequest } from "../../lib/api";

export type BatchStatus = "pending" | "approved" | "rejected";
export interface OrderLine {
  id: number;
  menu_item: number;
  item_name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
  created_at: string;
}
export interface Batch {
  id: string;
  order: string;
  sequence: number;
  status: BatchStatus;
  table_name: string;
  submitted_by: number;
  submitted_by_name: string;
  submitted_at: string;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  rejection_reason: string;
  lines: OrderLine[];
  total: string;
}
export interface OrderDetail {
  id: string;
  session: string;
  table: number;
  table_name: string;
  state: "open" | "closed";
  opened_at: string;
  batches: Batch[];
  totals: Record<BatchStatus, string>;
  events: {
    id: number;
    kind: string;
    actor_name: string;
    created_at: string;
    reason: string;
  }[];
}
export interface Submission {
  idempotency_key: string;
  lines: { menu_item: number; quantity: number }[];
}
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const orderApi = {
  active: async (table: number) =>
    (
      await workspaceRequest<{ order: OrderDetail | null }>(
        `orders/tables/${table}/active/`,
      )
    ).order,
  open: (table: number) =>
    workspaceRequest<OrderDetail>(`orders/tables/${table}/open/`, "POST", {}),
  detail: (id: string) => workspaceRequest<OrderDetail>(`orders/${id}/`),
  submit: (id: string, payload: Submission) =>
    workspaceRequest<Batch>(`orders/${id}/batches/`, "POST", payload),
  batches: (status: BatchStatus | "all", page = 1) =>
    workspaceRequest<Page<Batch>>(
      `orders/batches/?status=${status}&page=${page}`,
    ),
  approve: (id: string) =>
    workspaceRequest<Batch>(`orders/batches/${id}/approve/`, "POST", {}),
  reject: (id: string, reason: string) =>
    workspaceRequest<Batch>(`orders/batches/${id}/reject/`, "POST", { reason }),
};

// Integer minor units keep composer arithmetic exact. The server owns final prices.
export function minorUnits(amount: string): bigint {
  const [whole, fraction = ""] = amount.split(".");
  return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
}
export function money(amount: string | bigint): string {
  const cents = typeof amount === "bigint" ? amount : minorUnits(amount);
  return `NPR ${new Intl.NumberFormat("en-NP").format(cents / 100n)}.${String(cents % 100n).padStart(2, "0")}`;
}
export function localTime(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kathmandu",
  }).format(new Date(value));
}
