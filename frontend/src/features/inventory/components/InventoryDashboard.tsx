import { Link, Route, Routes } from "react-router";
import { InventoryItems } from "./InventoryItems";
import { StockReceiving } from "./StockReceiving";
import { StockAdjustments } from "./StockAdjustments";
import { RecipeManagement } from "./RecipeManagement";
import { MovementHistory } from "./MovementHistory";

export function InventoryDashboard() {
    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">Inventory Dashboard</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                <Link to="/inventory/items" className="p-6 bg-white shadow rounded border hover:border-green-500 block">
                    <h2 className="text-lg font-semibold">Manage Items</h2>
                    <p className="text-gray-500 text-sm mt-2">Create and view inventory ingredients.</p>
                </Link>
                <Link to="/inventory/receive" className="p-6 bg-white shadow rounded border hover:border-green-500 block">
                    <h2 className="text-lg font-semibold">Receive Stock</h2>
                    <p className="text-gray-500 text-sm mt-2">Record purchase receipts to increase stock.</p>
                </Link>
                <Link to="/inventory/adjust" className="p-6 bg-white shadow rounded border hover:border-green-500 block">
                    <h2 className="text-lg font-semibold">Stock Adjustments</h2>
                    <p className="text-gray-500 text-sm mt-2">Manually adjust quantities (e.g., physical counts).</p>
                </Link>
                <Link to="/inventory/recipes" className="p-6 bg-white shadow rounded border hover:border-green-500 block">
                    <h2 className="text-lg font-semibold">Recipe Management</h2>
                    <p className="text-gray-500 text-sm mt-2">Map menu items to ingredients for auto-consumption.</p>
                </Link>
                <Link to="/inventory/history" className="p-6 bg-white shadow rounded border hover:border-green-500 block">
                    <h2 className="text-lg font-semibold">Movement History</h2>
                    <p className="text-gray-500 text-sm mt-2">View the complete ledger of stock changes.</p>
                </Link>
            </div>

            <Routes>
                <Route path="items" element={<InventoryItems />} />
                <Route path="receive" element={<StockReceiving />} />
                <Route path="adjust" element={<StockAdjustments />} />
                <Route path="recipes" element={<RecipeManagement />} />
                <Route path="history" element={<MovementHistory />} />
            </Routes>
        </div>
    );
}
