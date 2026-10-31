import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { getInventoryItems } from "../api/inventoryApi";
import type { InventoryItem } from "../api/types";
import { workspaceRequest } from "../../../lib/api";

export function StockAdjustments() {
    const navigate = useNavigate();
    const [items, setItems] = useState<InventoryItem[]>([]);

    const [selectedItem, setSelectedItem] = useState<number | "">("");
    const [newQuantity, setNewQuantity] = useState("");
    const [reason, setReason] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        getInventoryItems().then(setItems).catch(console.error);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedItem) return;

        setSubmitting(true);
        try {
            await workspaceRequest(`inventory/items/${selectedItem}/adjust/`, "POST", {
                new_quantity: newQuantity,
                reason
            });
            alert("Stock adjusted successfully!");
            navigate("/inventory");
        } catch (err) {
            console.error(err);
            alert("Failed to adjust stock.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-6 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Stock Adjustments</h1>

            <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded shadow border">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Item</label>
                    <select
                        required
                        value={selectedItem}
                        onChange={e => setSelectedItem(e.target.value ? Number(e.target.value) : "")}
                        className="w-full border p-2 rounded"
                    >
                        <option value="">-- Select Item --</option>
                        {items.map(item => (
                            <option key={item.id} value={item.id}>{item.name} ({item.current_quantity} {item.base_unit} currently recorded)</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Actual Physical Quantity</label>
                    <input
                        required
                        type="number"
                        step="0.001"
                        min="0"
                        value={newQuantity}
                        onChange={e => setNewQuantity(e.target.value)}
                        className="w-full border p-2 rounded"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Adjustment</label>
                    <input
                        required
                        type="text"
                        value={reason}
                        onChange={e => setReason(e.target.value)}
                        className="w-full border p-2 rounded"
                        placeholder="e.g. Weekly physical count, spilled, damaged..."
                    />
                </div>

                <button
                    type="submit"
                    disabled={submitting || !selectedItem}
                    className="w-full py-2 bg-yellow-600 text-white rounded font-medium disabled:opacity-50 hover:bg-yellow-700"
                >
                    {submitting ? "Processing..." : "Confirm Adjustment"}
                </button>
            </form>
        </div>
    );
}
