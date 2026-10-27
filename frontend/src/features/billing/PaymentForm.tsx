import React, { useState } from "react";
import { Button, Input } from "../../components/ui";

interface PaymentFormProps {
  billId: string;
  maxAmount: number;
  onPaymentSuccess: () => void;
}

export function PaymentForm({ billId, maxAmount, onPaymentSuccess }: PaymentFormProps) {
  const [amount, setAmount] = useState<string>(maxAmount.toString());
  const [method, setMethod] = useState<string>("cash");
  const [reference, setReference] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    // Simple idempotency key generation for frontend
    const idempotencyKey = crypto.randomUUID();

    try {
      const response = await fetch(`/api/v1/billing/bill/${billId}/payments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: parseFloat(amount),
          method,
          manual_reference: reference,
          idempotency_key: idempotencyKey,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Payment failed");
      }

      onPaymentSuccess();
      setAmount("0");
      setReference("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="text-red-500 text-sm">{error}</div>}

      <div>
        <label htmlFor="amount" className="block text-sm font-medium mb-1">Amount (NPR)</label>
        <Input
          id="amount"
          type="number"
          step="0.01"
          min="0.01"
          max={maxAmount}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Method</label>
        <select
          className="input w-full"
          value={method}
          onChange={(e) => setMethod(e.target.value)}
        >
          <option value="cash">Cash</option>
          <option value="card">Card terminal / POS</option>
          <option value="digital_wallet">QR / Digital Wallet</option>
        </select>
      </div>

      {method !== "cash" && (
        <div>
          <label className="block text-sm font-medium mb-1">Reference (Optional)</label>
          <Input
            type="text"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="Txn ID"
          />
        </div>
      )}

      <Button
        type="submit"
        variant="primary"
        className="w-full"
        loading={submitting}
        disabled={submitting || parseFloat(amount) <= 0 || parseFloat(amount) > maxAmount}
      >
        Record Payment
      </Button>
    </form>
  );
}
