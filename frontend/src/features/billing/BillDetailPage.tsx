import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useAuth } from "../../auth/auth-context";
import { Alert, Spinner } from "../../components/ui";
import { billingApi, type BillDetail } from "./api";
import { PaymentForm } from "./PaymentForm";

export function BillDetailPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { session_id } = useParams<{ session_id: string }>();

  const [bill, setBill] = useState<BillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "cashier" && user?.role !== "owner" && user?.role !== "manager") {
      navigate("/");
      return;
    }

    if (!session_id) return;
    fetchBill(session_id);
  }, [user, navigate, session_id]);

  const fetchBill = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await billingApi.billDetail(id);
      setBill(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFinalize = async () => {
    if (!bill) return;
    try {
      const updated = await billingApi.finalizeBill(bill.id);
      setBill(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleCheckout = async () => {
    if (!session_id) return;
    try {
      await billingApi.checkoutSession(session_id);
      navigate("/billing");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handlePrint = async () => {
    if (!bill) return;
    try {
      await billingApi.printReceipt(bill.id);
      alert("Receipt sent to printer.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return <Alert title="Error loading bill" kind="error">{error}</Alert>;
  }

  if (!bill) {
    return <Alert title="Not found" kind="error">No bill found for this session.</Alert>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/billing" className="text-link text-sm mb-2 inline-block">&larr; Back to Billing</Link>
          <h1 className="text-2xl font-bold">Bill {bill.human_id}</h1>
          <p className="text-muted mt-1">
            Status:{" "}
            <span className={`badge ${
              bill.status === "paid" ? "badge-success" :
              bill.status === "partially_paid" ? "badge-warning" :
              "badge-secondary"
            }`}>
              {bill.status.replace("_", " ").toUpperCase()}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          {bill.status === "draft" && (
            <button className="btn btn-primary" onClick={handleFinalize}>
              Finalize Bill
            </button>
          )}
          {(bill.status === "finalized" || bill.status === "partially_paid" || bill.status === "paid") && (
            <button className="btn btn-secondary" onClick={handlePrint}>
              Print Receipt
            </button>
          )}
          {bill.status === "paid" && (
            <button className="btn btn-primary" onClick={handleCheckout}>
              Checkout Table
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-6">
          <h2 className="text-lg font-bold mb-4">Order Items</h2>
          <div className="space-y-2">
            {bill.lines.length === 0 ? (
              <p className="text-muted">No items yet.</p>
            ) : (
              bill.lines.map((line) => (
                <div key={line.id} className="flex justify-between border-b pb-2">
                  <div>
                    <p className="font-medium">{line.item_name}</p>
                    <p className="text-sm text-muted">{line.quantity} x NPR {line.unit_price}</p>
                  </div>
                  <p className="font-medium">NPR {line.line_total}</p>
                </div>
              ))
            )}
          </div>
          <div className="mt-4 pt-4 border-t flex justify-end">
            <div className="text-right">
              <p className="text-lg">Grand Total: <strong>NPR {bill.grand_total}</strong></p>
              <p className="text-muted">Paid: NPR {bill.paid_amount}</p>
              <p className="text-red-600 font-bold mt-1">Due: NPR {bill.outstanding_amount}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-bold mb-4">Record Payment</h2>
          {bill.status === "draft" ? (
            <Alert kind="warning">Finalize the bill first to accept payments.</Alert>
          ) : parseFloat(bill.outstanding_amount) <= 0 ? (
            <Alert kind="success">Bill is fully paid.</Alert>
          ) : (
            <PaymentForm
              billId={bill.id}
              maxAmount={parseFloat(bill.outstanding_amount)}
              onPaymentSuccess={() => session_id && fetchBill(session_id)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
