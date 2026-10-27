import { Outlet } from "react-router";
import { useAuth } from "../../auth/auth-context";
import { Notice } from "../../components/ui";

export function OrdersAccess({ role }: { role: "waiter" | "cashier" | "chef" }) {
  const { user } = useAuth();
  return user?.role === role ? (
    <Outlet key={`${role}:${user.id}`} />
  ) : (
    <Notice>Your role cannot access this screen.</Notice>
  );
}
