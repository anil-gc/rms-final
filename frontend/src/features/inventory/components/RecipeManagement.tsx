import { useEffect, useState } from "react";
import { getInventoryItems, getRecipes } from "../api/inventoryApi";
import type { InventoryItem, RecipeIngredient } from "../api/types";
import { workspaceRequest } from "../../../lib/api";
import { useResource } from "../../../hooks/useResource";

export function RecipeManagement() {
    const { data: menuData } = useResource(() => workspaceRequest("menu/items/"));
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const menuItems = (menuData as any)?.results || [];

    const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([]);
    const [recipes, setRecipes] = useState<RecipeIngredient[]>([]);

    // Form state
    const [menuItemId, setMenuItemId] = useState("");
    const [inventoryItemId, setInventoryItemId] = useState("");
    const [quantity, setQuantity] = useState("");
    const [unit, setUnit] = useState("g");
    const [submitting, setSubmitting] = useState(false);

    const load = () => {
        getInventoryItems().then(setInventoryItems).catch(console.error);
        getRecipes().then(setRecipes).catch(console.error);
    };

    useEffect(() => { load(); }, []);

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            await workspaceRequest("inventory/recipes/", "POST", {
                menu_item: Number(menuItemId),
                inventory_item: Number(inventoryItemId),
                quantity,
                unit
            });
            load();
            setMenuItemId("");
            setInventoryItemId("");
            setQuantity("");
        } catch (err) {
            console.error(err);
            alert("Failed to add recipe mapping.");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto space-y-8">
            <h1 className="text-2xl font-bold">Recipe Configuration</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Form */}
                <form onSubmit={handleAdd} className="space-y-4 bg-white p-6 rounded shadow border">
                    <h2 className="text-lg font-semibold border-b pb-2 mb-4">Add Ingredient to Menu Item</h2>

                    <div>
                        <label className="block text-sm font-medium mb-1">Menu Item</label>
                        <select required value={menuItemId} onChange={e => setMenuItemId(e.target.value)} className="w-full border p-2 rounded">
                            <option value="">-- Select Menu Item --</option>
                            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                            {menuItems.map((item: any) => (
                                <option key={item.id} value={item.id}>{item.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Inventory Ingredient</label>
                        <select required value={inventoryItemId} onChange={e => setInventoryItemId(e.target.value)} className="w-full border p-2 rounded">
                            <option value="">-- Select Inventory Item --</option>
                            {inventoryItems.map(item => (
                                <option key={item.id} value={item.id}>{item.name} (Tracks in {item.base_unit})</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-1">Quantity Required</label>
                            <input required type="number" step="0.001" min="0" value={quantity} onChange={e => setQuantity(e.target.value)} className="w-full border p-2 rounded" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">Unit</label>
                            <select value={unit} onChange={e => setUnit(e.target.value)} className="w-full border p-2 rounded">
                                <option value="kg">kg</option>
                                <option value="g">g</option>
                                <option value="L">L</option>
                                <option value="ml">ml</option>
                                <option value="pcs">pcs</option>
                                <option value="pkt">pkt</option>
                            </select>
                        </div>
                    </div>

                    <button type="submit" disabled={submitting} className="w-full mt-4 bg-blue-600 text-white py-2 rounded">
                        {submitting ? "Saving..." : "Add to Recipe"}
                    </button>
                </form>

                {/* List */}
                <div className="bg-white p-6 rounded shadow border">
                    <h2 className="text-lg font-semibold mb-4">Current Recipe Mappings</h2>
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Menu Item ID</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Ingredient</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Quantity</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                            {recipes.map(r => (
                                <tr key={r.id}>
                                    <td className="px-4 py-2 text-sm">{r.menu_item}</td>
                                    <td className="px-4 py-2 text-sm">{r.inventory_item_name}</td>
                                    <td className="px-4 py-2 text-sm">{parseFloat(r.quantity).toString()} {r.unit}</td>
                                </tr>
                            ))}
                            {recipes.length === 0 && (
                                <tr>
                                    <td colSpan={3} className="px-4 py-2 text-center text-sm text-gray-500">No recipes configured.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
