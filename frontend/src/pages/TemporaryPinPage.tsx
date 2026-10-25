import { Navigate, useNavigate } from "react-router";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { CredentialForm } from "./ProfilePage";
import { ActionError, Brand, Button, Notice } from "../components/ui";
import { useAction } from "../hooks/useAction";

export function TemporaryPinPage() {
  const { user, logout } = useAuth();
  const action = useAction();
  const navigate = useNavigate();
  if (!user) return null;
  if (!user.must_change_pin) return <Navigate to="/" replace />;
  return (
    <div className="pin-page">
      <header>
        <Brand dark />
        <span className="pin-user">
          Signed in as <strong>{user.username}</strong>
        </span>
      </header>
      <main className="pin-card card">
        <div className="pin-heading">
          <span className="login-icon">
            <KeyRound size={26} />
          </span>
          <span className="eyebrow">ONE SMALL STEP TO MAKE IT YOURS</span>
          <h1>Choose your own PIN.</h1>
          <p>
            Your Owner gave you a temporary PIN. Replace it with one only you
            know to enter your workspace.
          </p>
        </div>
        {user.role === "owner" ? (
          <Notice>
            This account needs an administrator’s attention before continuing.
            Please contact your system administrator.
          </Notice>
        ) : (
          <CredentialForm
            required
            onComplete={() => navigate("/", { replace: true })}
          />
        )}
        <div className="security-footer">
          <ShieldCheck size={17} />
          <p>Your workspace stays locked until this step is complete.</p>
        </div>
        <ActionError error={action.error} remaining={action.remaining} />
        <Button
          variant="ghost"
          className="w-full mt-4"
          loading={action.pending}
          disabled={action.remaining > 0}
          onClick={() => void action.run(logout)}
        >
          <LogOut size={16} />
          Sign out instead
        </Button>
      </main>
      <footer>Personal access. A more connected team.</footer>
    </div>
  );
}
