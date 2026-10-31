import { useEffect, useState } from "react";
import { getMovements } from "../api/inventoryApi";
import type { StockMovement } from "../api/types";

export function MovementHistory() {
    const [movements, setMovements] = useState<StockMovement[]>([]);

    useEffect(() => {
        getMovements().then(res => setMovements(res.results)).catch(console.error);
    }, []);

    return (
        <div className="bg-white p-6 rounded shadow mt-6 border">
            <h1 className="text-2xl font-bold mb-6">Movement History</h1>
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-4 py-2 text-left font-medium text-gray-500">Date</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500">Item</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500">Type</th>
                            <th className="px-4 py-2 text-right font-medium text-gray-500">Delta</th>
                            <th className="px-4 py-2 text-right font-medium text-gray-500">New Balance</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500">Actor</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-500">Reason/Ref</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                        {movements.map(m => (
                            <tr key={m.id}>
                                <td className="px-4 py-2 whitespace-nowrap text-gray-500">
                                    {new Date(m.timestamp).toLocaleString()}
                                </td>
                                <td className="px-4 py-2 font-medium">{m.item_name}</td>
                                <td className="px-4 py-2 uppercase text-xs tracking-wider">{m.movement_type.replace('_', ' ')}</td>
                                <td className={`px-4 py-2 text-right font-bold ${parseFloat(m.quantity_delta) > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {parseFloat(m.quantity_delta) > 0 ? '+' : ''}{parseFloat(m.quantity_delta).toString()}
                                </td>
                                <td className="px-4 py-2 text-right">{m.new_balance ? parseFloat(m.new_balance).toString() : '-'}</td>
                                <td className="px-4 py-2 text-gray-500">{m.actor_name || 'System'}</td>
                                <td className="px-4 py-2 text-gray-500 truncate max-w-xs">{m.reason || m.reference}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
