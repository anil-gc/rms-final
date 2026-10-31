import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { getInventoryItems } from "../api/inventoryApi";
import type { InventoryItem } from "../api/types";
import { workspaceRequest } from "../../../lib/api";

export function StockReceiving() {
    const navigate = useNavigate();
    const [items, setItems] = useState<InventoryItem[]>([]);

    // Form state
    const [selectedItem, setSelectedItem] = useState<number | "">("");
    const [quantity, setQuantity] = useState("");
    const [unit, setUnit] = useState("kg");
    const [notes, setNotes] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        getInventoryItems().then(setItems).catch(console.error);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedItem) return;

        setSubmitting(true);
        try {
            await workspaceRequest(`inventory/items/${selectedItem}/receive/`, "POST", {
                quantity,
                unit,
                notes
            });
            alert("Stock received successfully!");
            navigate("/inventory");
        } catch (err) {
            console.error(err);
            alert("Failed to receive stock.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-6 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Receive Stock</h1>

            <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded shadow border">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Select Item</label>
                    <select
                        required
                        value={selectedItem}
                        onChange={e => setSelectedItem(e.target.value ? Number(e.target.value) : "")}
                        className="w-full border p-2 rounded"
                    >
                        <option value="">-- Select Item --</option>
                        {items.map(item => (
                            <option key={item.id} value={item.id}>{item.name}</option>
                        ))}
                    </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Quantity Received</label>
                        <input
                            required
                            type="number"
                            step="0.001"
                            min="0"
                            value={quantity}
                            onChange={e => setQuantity(e.target.value)}
                            className="w-full border p-2 rounded"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Unit Received</label>
                        <select
                            required
                            value={unit}
                            onChange={e => setUnit(e.target.value)}
                            className="w-full border p-2 rounded"
                        >
                            <option value="kg">Kilogram (kg)</option>
                            <option value="g">Gram (g)</option>
                            <option value="L">Liter (L)</option>
                            <option value="ml">Milliliter (ml)</option>
                            <option value="pcs">Piece (pcs)</option>
                            <option value="pkt">Packet (pkt)</option>
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Notes / Supplier info (optional)</label>
                    <input
                        type="text"
                        value={notes}
                        onChange={e => setNotes(e.target.value)}
                        className="w-full border p-2 rounded"
                    />
                </div>

                <button
                    type="submit"
                    disabled={submitting || !selectedItem}
                    className="w-full py-2 bg-green-600 text-white rounded font-medium disabled:opacity-50 hover:bg-green-700"
                >
                    {submitting ? "Processing..." : "Confirm Receipt"}
                </button>
            </form>
        </div>
    );
}
