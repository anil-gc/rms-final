import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../../auth/auth-context";
import { Alert, Spinner } from "../../components/ui";

interface BillSummary {
  id: string;
  human_id: string;
  session: string;
  status: string;
  grand_total: string;
  paid_amount: string;
  outstanding_amount: string;
}

export function BillingDashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [bills, setBills] = useState<BillSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (user?.role !== "cashier" && user?.role !== "owner" && user?.role !== "manager") {
      navigate("/");
      return;
    }

    const fetchBills = async () => {
      try {
        const response = await fetch("/api/v1/billing/active-tables/");
        if (!response.ok) throw new Error("Failed to fetch active bills");
        const data = await response.json();
        setBills(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setLoading(false);
      }
    };

    fetchBills();
  }, [user, navigate]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return <Alert title="Error loading billing dashboard" kind="error">{error.message}</Alert>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Billing & Payments</h1>
          <p className="text-muted mt-1">Manage active table bills and process payments.</p>
        </div>
      </div>

      {bills.length === 0 ? (
        <div className="card p-12 text-center text-muted">
          <p>No active bills found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bills.map((bill) => (
            <div key={bill.id} className="card p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold text-lg">{bill.human_id}</span>
                  <span className={`badge ${
                    bill.status === "paid" ? "badge-success" :
                    bill.status === "partially_paid" ? "badge-warning" :
                    "badge-secondary"
                  }`}>
                    {bill.status.replace("_", " ").toUpperCase()}
                  </span>
                </div>

                <div className="space-y-1 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Total</span>
                    <span className="font-medium">NPR {bill.grand_total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Paid</span>
                    <span className="font-medium">NPR {bill.paid_amount}</span>
                  </div>
                  <div className="flex justify-between border-t pt-1 mt-1">
                    <span className="font-bold">Due</span>
                    <span className="font-bold text-red-600">NPR {bill.outstanding_amount}</span>
                  </div>
                </div>
              </div>

              <Link to={`/billing/${bill.session}`} className="btn btn-primary w-full text-center">
                View Bill
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
