import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import {
  ArrowUpRight,
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  ShieldCheck,
  UserRound,
  UsersRound,
  Store,
  Utensils,
  Armchair,
} from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { displayName, roleLabel } from "../types";
import { ActionError, Avatar, Brand, Button, Dialog } from "./ui";
import { useAction } from "../hooks/useAction";

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const links = [
    { to: "/", label: "Overview", icon: LayoutDashboard },
    { to: "/restaurant", label: "Restaurant profile", icon: Store },
    { to: "/menu", label: "Menu catalogue", icon: Utensils },
    { to: "/tables", label: "Tables", icon: Armchair },
    ...(user?.role === "owner"
      ? [{ to: "/staff", label: "Staff management", icon: UsersRound }]
      : []),
    { to: "/profile", label: "My profile", icon: UserRound },
  ];
  return (
    <nav aria-label="Main navigation" className="sidebar-nav">
      <p className="nav-heading">YOUR WORKSPACE</p>
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            `nav-link ${isActive ? "is-active" : ""}`
          }
        >
          <Icon size={19} strokeWidth={1.8} />
          <span>{label}</span>
          <span className="nav-active-dot" />
        </NavLink>
      ))}
    </nav>
  );
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const action = useAction();
  const location = useLocation();
  if (!user) return null;
  const page = location.pathname.startsWith("/staff")
    ? "Staff management"
    : location.pathname === "/profile"
      ? "My profile"
      : location.pathname === "/restaurant"
        ? "Restaurant profile"
        : location.pathname === "/menu"
          ? "Menu catalogue"
          : location.pathname === "/tables"
            ? "Tables"
            : "Overview";
  const date = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kathmandu",
  }).format(new Date());
  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Brand />
          <span className="sidebar-brand-label">RESTAURANT WORKSPACE</span>
        </div>
        <Navigation />
        <div className="sidebar-note">
          <div className="sidebar-note-icon">
            <ShieldCheck size={22} />
          </div>
          <h3>A place for your people.</h3>
          <p>Clear access. A connected team. One shared workspace.</p>
        </div>
        <div className="sidebar-footer">
          <span className="sidebar-dot" />
          Your team, together.
        </div>
      </aside>
      {mobileOpen && (
        <Dialog
          title="Your workspace"
          className="mobile-drawer"
          onClose={() => setMobileOpen(false)}
        >
          <Navigation onNavigate={() => setMobileOpen(false)} />
        </Dialog>
      )}
      <div className="app-main">
        <header className="app-header">
          <div className="flex items-center gap-3">
            <button
              className="icon-button mobile-menu-button"
              aria-label="Open navigation"
              onClick={() => setMobileOpen(true)}
            >
              <Menu size={22} />
            </button>
            <div className="breadcrumbs">
              <span>Workspace</span>
              <span className="breadcrumb-slash">/</span>
              <strong>{page}</strong>
            </div>
          </div>
          <div className="header-right">
            <span className="header-date">{date}</span>
            <NavLink
              to="/profile"
              className="header-profile"
              aria-label="Open my profile"
            >
              <Avatar user={user} />
              <span>
                <strong>{displayName(user)}</strong>
                <small>{roleLabel(user.role)}</small>
              </span>
              <ChevronDown size={14} />
            </NavLink>
            <button
              className="icon-button header-logout"
              aria-label="Sign out"
              onClick={() => setConfirmLogout(true)}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main id="main-content" className="page-content" tabIndex={-1}>
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>
            RMS <span className="footer-divider">/</span> A little more
            organised.
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck size={13} /> Private team workspace
          </span>
        </footer>
      </div>
      {confirmLogout && (
        <Dialog
          title="Sign out of your workspace?"
          busy={action.pending}
          onClose={() => setConfirmLogout(false)}
        >
          <div className="dialog-body">
            <p className="text-muted">
              You’ll need your {user.role === "owner" ? "password" : "PIN"} to
              sign in again.
            </p>
            <ActionError error={action.error} remaining={action.remaining} />
            <div className="dialog-actions">
              <Button
                variant="secondary"
                disabled={action.pending}
                onClick={() => setConfirmLogout(false)}
              >
                Stay signed in
              </Button>
              <Button
                loading={action.pending}
                disabled={action.remaining > 0}
                onClick={() => void action.run(logout)}
              >
                Sign out <ArrowUpRight size={16} />
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
}
