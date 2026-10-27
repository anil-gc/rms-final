import { workspaceRequest } from "../../lib/api";

export type KitchenStatus = "pending" | "preparing" | "ready" | "served";

export interface KitchenTicket {
  ticket_id: string | null;
  order_line_id: number;
  item_name: string;
  quantity: number;
  table_name: string;
  order_id: string;
  batch_id: string;
  batch_sequence: number;
  status: KitchenStatus;
  created_at: string;
  approved_at: string;
  waiter_name: string;
}

export const kitchenApi = {
  tickets: (status?: KitchenStatus) =>
    workspaceRequest<KitchenTicket[]>(
      `kitchen/tickets/${status ? `?status=${status}` : ""}`,
    ),
  markPreparing: (lineId: number) =>
    workspaceRequest<KitchenTicket>(
      `kitchen/tickets/${lineId}/preparing/`,
      "POST",
      {},
    ),
  markReady: (lineId: number) =>
    workspaceRequest<KitchenTicket>(
      `kitchen/tickets/${lineId}/ready/`,
      "POST",
      {},
    ),
  markServed: (lineId: number) =>
    workspaceRequest<KitchenTicket>(
      `kitchen/tickets/${lineId}/served/`,
      "POST",
      {},
    ),
};
