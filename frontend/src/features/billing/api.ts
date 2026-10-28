import { workspaceRequest } from "../../lib/api";

export interface BillSummary {
  id: string;
  human_id: string;
  session: string;
  status: string;
  grand_total: string;
  paid_amount: string;
  outstanding_amount: string;
}

export interface PaymentPayload {
  amount: number;
  method: string;
  manual_reference?: string;
  idempotency_key: string;
}

export interface BillLine {
  id: string;
  item_name: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface BillDetail extends BillSummary {
  lines: BillLine[];
}

export const billingApi = {
  activeBills: () => workspaceRequest<BillSummary[]>("billing/active-tables/"),
  billDetail: (sessionId: string) => workspaceRequest<BillDetail>(`billing/session/${sessionId}/`),
  recordPayment: (billId: string, payload: PaymentPayload) =>
    workspaceRequest<unknown>(`billing/bill/${billId}/payments/`, "POST", payload),
  finalizeBill: (billId: string) => workspaceRequest<BillDetail>(`billing/bill/${billId}/finalize/`, "POST", {}),
  checkoutSession: (sessionId: string) => workspaceRequest<{ success: boolean }>(`billing/session/${sessionId}/checkout/`, "POST", {}),
  printReceipt: (billId: string) => workspaceRequest<unknown>(`billing/bill/${billId}/print/`, "POST", {}),
};
