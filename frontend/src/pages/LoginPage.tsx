import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, NavLink, useLocation, useNavigate } from "react-router";
import {
  ArrowRight,
  Check,
  KeyRound,
  LockKeyhole,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { useAction } from "../hooks/useAction";
import {
  ActionError,
  Brand,
  Button,
  Field,
  LoadingPage,
  SecretField,
} from "../components/ui";

export function LoginPage({ kind }: { kind: "owner" | "staff" }) {
  const { user, status, loginOwner, loginStaff } = useAuth();
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");
  const action = useAction();
  const navigate = useNavigate();
  const location = useLocation();
  if (status === "loading")
    return <LoadingPage message="Checking your session…" />;
  if (user && status === "authenticated")
    return <Navigate to={user.must_change_pin ? "/change-pin" : "/"} replace />;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const profile = await action.run(() =>
      kind === "owner"
        ? loginOwner(username.trim(), secret)
        : loginStaff(username.trim(), secret),
    );
    setSecret("");
    if (profile) {
      const target =
        location.state && typeof location.state === "object"
          ? location.state.from
          : undefined;
      const allowed =
        target === "/profile" ||
        (target === "/staff" && profile.role === "owner")
          ? target
          : "/";
      navigate(profile.must_change_pin ? "/change-pin" : allowed, {
        replace: true,
      });
    }
  }
  return (
    <div className="login-page">
      <section className="login-story">
        <Brand />
        <div className="login-story-main">
          <span className="eyebrow story-eyebrow">
            <span /> BUILT AROUND YOUR PEOPLE
          </span>
          <h1>
            Good service.
            <br />
            Great teamwork.
            <br />
            <em>It starts here.</em>
          </h1>
          <p>
            A thoughtful workspace for the people who keep your restaurant
            moving.
          </p>
          <div className="story-illustration" aria-hidden="true">
            <div className="plate plate-outer">
              <div className="plate plate-inner">
                <span>rms.</span>
              </div>
            </div>
            <div className="story-chip chip-one">
              <UsersRound size={18} /> Your team, connected
            </div>
            <div className="story-chip chip-two">
              <ShieldCheck size={18} /> Everyone has their place
            </div>
            <div className="story-spark spark-one" />
            <div className="story-spark spark-two" />
          </div>
        </div>
        <div className="story-footer">
          <span>
            <Check size={15} /> Owner-managed accounts
          </span>
          <span>
            <Check size={15} /> Secure staff access
          </span>
        </div>
      </section>
      <section className="login-form-area">
        <div className="mobile-login-brand">
          <Brand dark />
        </div>
        <div className="login-form-card">
          <div className="login-icon">
            {kind === "owner" ? (
              <ShieldCheck size={26} />
            ) : (
              <KeyRound size={26} />
            )}
          </div>
          <span className="eyebrow">WELCOME TO YOUR WORKSPACE</span>
          <h2>Good to have you back.</h2>
          <p className="login-description">
            Sign in to pick up where your team left off.
          </p>
          <nav className="login-tabs" aria-label="Sign-in type">
            <NavLink
              to="/login/owner"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Owner login
            </NavLink>
            <NavLink
              to="/login/staff"
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              Staff login
            </NavLink>
          </nav>
          <form onSubmit={submit} className="form-stack">
            <ActionError error={action.error} remaining={action.remaining} />
            <Field
              label="Username"
              name="username"
              autoComplete="username"
              placeholder={
                kind === "owner" ? "Your owner username" : "Your staff username"
              }
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={action.error?.fields.username}
              required
              maxLength={150}
            />
            <SecretField
              label={kind === "owner" ? "Password" : "PIN"}
              name={kind === "owner" ? "password" : "pin"}
              autoComplete="current-password"
              placeholder={
                kind === "owner"
                  ? "Enter your password"
                  : "Enter your 6-digit PIN"
              }
              pin={kind === "staff"}
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              error={
                action.error?.fields[kind === "owner" ? "password" : "pin"]
              }
              required
            />
            <Button
              type="submit"
              className="w-full login-submit"
              loading={action.pending}
              disabled={action.remaining > 0}
            >
              Sign in to workspace <ArrowRight size={18} />
            </Button>
          </form>
          <div className="login-help">
            <LockKeyhole size={16} />
            <p>
              {kind === "owner"
                ? "Use the password set up for your Owner account."
                : "Your Owner provides your username and temporary PIN."}
              <br />
              {kind === "staff"
                ? "Forgot your PIN? Ask your Owner to reset it."
                : "Need help signing in? Contact your system administrator."}
            </p>
          </div>
        </div>
        <footer className="login-form-footer">
          Made for restaurant teams. <span>Built with care.</span>
        </footer>
      </section>
    </div>
  );
}
