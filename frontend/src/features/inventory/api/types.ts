export interface InventoryItem {
    id: number;
    name: string;
    category: string;
    base_unit: string;
    current_quantity: string;
    min_stock_threshold: string;
    is_active: boolean;
    sku: string;
}

export interface StockMovement {
    id: string;
    item: number;
    item_name: string;
    quantity_delta: string;
    movement_type: string;
    actor_name: string;
    timestamp: string;
    reference: string;
    reason: string;
    previous_balance: string;
    new_balance: string;
}

export interface RecipeIngredient {
    id: number;
    menu_item: number;
    inventory_item: number;
    inventory_item_name: string;
    quantity: string;
    unit: string;
}
