import { ApiError, workspaceRequest } from "./api";

export interface Restaurant {
  id: number;
  name: string;
  description: string;
  address: string;
  contact_phone: string;
  email: string;
  logo_url: string | null;
  currency: "NPR";
  opening_time: string | null;
  closing_time: string | null;
  is_active: boolean;
  updated_at: string;
}
export type RestaurantInput = Omit<
  Restaurant,
  "id" | "logo_url" | "updated_at"
>;
export interface Category {
  id: number;
  name: string;
  description: string;
  sort_order: number;
  is_active: boolean;
  updated_at: string;
}
export type CategoryInput = Omit<Category, "id" | "updated_at">;
export interface MenuItem {
  id: number;
  name: string;
  description: string;
  category: number;
  category_name: string;
  price: string;
  is_available: boolean;
  effective_available: boolean;
  is_active: boolean;
  updated_at: string;
}
export type ItemInput = Omit<
  MenuItem,
  "id" | "category_name" | "effective_available" | "updated_at"
>;
export interface DiningTable {
  id: number;
  name: string;
  capacity: number;
  status: "available" | "occupied";
  is_active: boolean;
  updated_at: string;
}
export type TableInput = Omit<DiningTable, "id" | "updated_at">;

export const canManageWorkspace = (role?: string) =>
  role === "owner" || role === "manager";
export const formatNpr = (price: string) =>
  new Intl.NumberFormat("en-NP", {
    style: "currency",
    currency: "NPR",
    minimumFractionDigits: 2,
  }).format(Number(price));

export const workspace = {
  restaurant: async () => {
    try {
      return await workspaceRequest<Restaurant>("restaurant/");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },
  saveRestaurant: (data: RestaurantInput, exists: boolean) =>
    workspaceRequest<Restaurant>(
      "restaurant/",
      exists ? "PATCH" : "POST",
      data,
    ),
  uploadLogo: (file: File) => {
    const data = new FormData();
    data.append("logo", file);
    return workspaceRequest<Restaurant>("restaurant/logo/", "POST", data);
  },
  removeLogo: () => workspaceRequest<void>("restaurant/logo/", "DELETE"),
  categories: () => workspaceRequest<Category[]>("menu/categories/"),
  saveCategory: (data: CategoryInput, id?: number) =>
    workspaceRequest<Category>(
      `menu/categories/${id ? `${id}/` : ""}`,
      id ? "PATCH" : "POST",
      data,
    ),
  items: () => workspaceRequest<MenuItem[]>("menu/items/"),
  saveItem: (data: ItemInput, id?: number) =>
    workspaceRequest<MenuItem>(
      `menu/items/${id ? `${id}/` : ""}`,
      id ? "PATCH" : "POST",
      data,
    ),
  tables: () => workspaceRequest<DiningTable[]>("tables/"),
  saveTable: (data: TableInput, id?: number) =>
    workspaceRequest<DiningTable>(
      `tables/${id ? `${id}/` : ""}`,
      id ? "PATCH" : "POST",
      data,
    ),
};
