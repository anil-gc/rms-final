import { Navigate, Outlet, useLocation } from "react-router";
import { RefreshCw, ShieldX } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "./auth-context";
import { Button, Brand, LoadingPage } from "../components/ui";

export function ProtectedRoute({
  ownerOnly = false,
  allowTemporary = false,
}: {
  ownerOnly?: boolean;
  allowTemporary?: boolean;
}) {
  const { user, status, refresh, loginPath } = useAuth();
  const location = useLocation();
  if (status === "loading") return <LoadingPage />;
  if (status === "unavailable")
    return (
      <div className="connection-page">
        <Brand />
        <div className="card connection-card">
          <RefreshCw size={30} />
          <h1>Let’s reconnect.</h1>
          <p>
            We couldn’t check your session. Your account hasn’t been signed out.
          </p>
          <Button onClick={() => void refresh()}>
            Try again <RefreshCw size={16} />
          </Button>
        </div>
      </div>
    );
  if (!user)
    return (
      <Navigate to={loginPath} replace state={{ from: location.pathname }} />
    );
  if (user.must_change_pin && !allowTemporary)
    return <Navigate to="/change-pin" replace />;
  if (ownerOnly && user.role !== "owner")
    return (
      <div className="access-denied card">
        <ShieldX size={34} />
        <h1>Owner access required</h1>
        <p>
          Your role doesn’t include staff management. You can still access your
          account.
        </p>
        <Link className="btn btn-primary" to="/">
          Back to overview
        </Link>
      </div>
    );
  return <Outlet />;
}
