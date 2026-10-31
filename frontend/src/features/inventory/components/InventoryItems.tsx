import { useEffect, useState } from "react";
import { getInventoryItems } from "../api/inventoryApi";
import type { InventoryItem } from "../api/types";
import { workspaceRequest } from "../../../lib/api";

export function InventoryItems() {
    const [items, setItems] = useState<InventoryItem[]>([]);
    const [showAdd, setShowAdd] = useState(false);

    // Form state
    const [name, setName] = useState("");
    const [category, setCategory] = useState("");
    const [baseUnit, setBaseUnit] = useState("kg");
    const [threshold, setThreshold] = useState("0");

    const load = () => {
        getInventoryItems().then(setItems).catch(console.error);
    };

    useEffect(() => { load(); }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await workspaceRequest("inventory/items/", "POST", {
                name,
                category,
                base_unit: baseUnit,
                min_stock_threshold: threshold
            });
            setShowAdd(false);
            load();
        } catch (err) {
            console.error(err);
            alert("Failed to add item");
        }
    };

    return (
        <div className="bg-white p-6 rounded shadow mt-6 border">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Inventory Items</h1>
                <button
                    className="bg-green-700 text-white px-4 py-2 rounded font-medium"
                    onClick={() => setShowAdd(!showAdd)}
                >
                    {showAdd ? "Cancel" : "Add Item"}
                </button>
            </div>

            {showAdd && (
                <form onSubmit={handleAdd} className="mb-8 p-4 border rounded bg-gray-50">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">Name</label>
                            <input required value={name} onChange={e => setName(e.target.value)} className="w-full border p-2 rounded" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Category</label>
                            <input required value={category} onChange={e => setCategory(e.target.value)} className="w-full border p-2 rounded" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Base Unit</label>
                            <select value={baseUnit} onChange={e => setBaseUnit(e.target.value)} className="w-full border p-2 rounded">
                                <option value="kg">Kilogram (kg)</option>
                                <option value="g">Gram (g)</option>
                                <option value="L">Liter (L)</option>
                                <option value="ml">Milliliter (ml)</option>
                                <option value="pcs">Piece (pcs)</option>
                                <option value="pkt">Packet (pkt)</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Low Stock Threshold</label>
                            <input required type="number" step="0.001" value={threshold} onChange={e => setThreshold(e.target.value)} className="w-full border p-2 rounded" />
                        </div>
                    </div>
                    <button type="submit" className="mt-4 bg-blue-600 text-white px-4 py-2 rounded">Save Item</button>
                </form>
            )}

            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                            <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Current Stock</th>
                            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {items.map(item => {
                            const qty = parseFloat(item.current_quantity);
                            const thresh = parseFloat(item.min_stock_threshold);
                            const isLow = qty <= thresh;

                            return (
                                <tr key={item.id}>
                                    <td className="px-4 py-2 text-sm font-medium text-gray-900">{item.name}</td>
                                    <td className="px-4 py-2 text-sm text-gray-500">{item.category}</td>
                                    <td className="px-4 py-2 text-sm text-right font-medium">
                                        {qty.toString()} {item.base_unit}
                                    </td>
                                    <td className="px-4 py-2 text-sm">
                                        {isLow ? (
                                            <span className="text-red-600 bg-red-100 px-2 py-1 rounded text-xs font-bold">LOW STOCK</span>
                                        ) : (
                                            <span className="text-green-600 bg-green-100 px-2 py-1 rounded text-xs">OK</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                        {items.length === 0 && (
                            <tr>
                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">No inventory items found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
