import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthProvider";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";
import { Brand } from "./components/ui";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { StaffPage } from "./pages/StaffPage";
import { ProfilePage } from "./pages/ProfilePage";
import { TemporaryPinPage } from "./pages/TemporaryPinPage";
import { RestaurantPage } from "./pages/RestaurantPage";
import { MenuPage } from "./pages/MenuPage";
import { TablesPage } from "./pages/TablesPage";
import { WaiterOrdersPage } from "./features/orders/WaiterOrdersPage";
import { CashierOrdersPage } from "./features/orders/CashierOrdersPage";
import { OrdersAccess } from "./features/orders/OrdersAccess";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/login/owner" replace />} />
      <Route
        path="/login/owner"
        element={<LoginPage key="owner" kind="owner" />}
      />
      <Route
        path="/login/staff"
        element={<LoginPage key="staff" kind="staff" />}
      />
      <Route element={<ProtectedRoute allowTemporary />}>
        <Route path="/change-pin" element={<TemporaryPinPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/restaurant" element={<RestaurantPage />} />
          <Route path="/menu" element={<MenuPage />} />
          <Route path="/tables" element={<TablesPage />} />
          <Route element={<OrdersAccess role="waiter" />}>
            <Route path="/orders/waiter" element={<WaiterOrdersPage />} />
          </Route>
          <Route element={<OrdersAccess role="cashier" />}>
            <Route path="/orders/cashier" element={<CashierOrdersPage />} />
          </Route>
          <Route element={<ProtectedRoute ownerOnly />}>
            <Route path="/staff" element={<StaffPage />} />
          </Route>
        </Route>
      </Route>
      <Route
        path="*"
        element={
          <div className="connection-page">
            <Brand dark />
            <div className="card connection-card">
              <span className="eyebrow">404 · PAGE NOT FOUND</span>
              <h1>A little off the menu.</h1>
              <p>
                This page doesn’t exist. Let’s get you back to your workspace.
              </p>
              <Link className="btn btn-primary" to="/">
                Back to workspace
              </Link>
            </div>
          </div>
        }
      />
    </Routes>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
