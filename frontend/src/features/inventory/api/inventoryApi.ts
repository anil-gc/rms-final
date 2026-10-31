import { workspaceRequest } from "../../../lib/api";
import type { InventoryItem, RecipeIngredient, StockMovement } from "./types";

export const getInventoryItems = async (): Promise<InventoryItem[]> => {
    return workspaceRequest("/api/v1/inventory/items/");
};

export const getMovements = async (): Promise<{ results: StockMovement[] }> => {
    return workspaceRequest("/api/v1/inventory/movements/");
};

export const getRecipes = async (): Promise<RecipeIngredient[]> => {
    return workspaceRequest("/api/v1/inventory/recipes/");
};
