import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Check,
  KeyRound,
  ShieldCheck,
  UserRound,
  UsersRound,
  UserCheck,
} from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "../auth/auth-context";
import { useStaff } from "../hooks/useStaff";
import {
  Avatar,
  Button,
  Notice,
  RoleBadge,
  StatusBadge,
} from "../components/ui";
import { displayName, roleLabel } from "../types";

export function DashboardPage() {
  const { user } = useAuth();
  const team = useStaff(user?.role === "owner");
  if (!user) return null;
  const owner = user.role === "owner";
  const date = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    timeZone: "Asia/Kathmandu",
  }).format(new Date());
  const stats = owner
    ? [
        {
          label: "Team members",
          value: team.staff?.length,
          hint: "People in your workspace",
          icon: UsersRound,
          tone: "peach",
        },
        {
          label: "Active accounts",
          value: team.staff?.filter((member) => member.is_active).length,
          hint: "Staff with sign-in access",
          icon: UserCheck,
          tone: "sage",
        },
        {
          label: "PIN changes needed",
          value: team.staff?.filter(
            (member) => member.is_active && member.must_change_pin,
          ).length,
          hint: "Active accounts with a temporary PIN",
          icon: KeyRound,
          tone: "sand",
        },
        {
          label: "Your role",
          value: roleLabel(user.role),
          hint: "Team and account management",
          icon: ShieldCheck,
          tone: "lavender",
        },
      ]
    : [
        {
          label: "Your role",
          value: roleLabel(user.role),
          hint: "Assigned by your Owner",
          icon: UserRound,
          tone: "peach",
        },
        {
          label: "Account access",
          value: "Active",
          hint: "Your account is ready to use",
          icon: UserCheck,
          tone: "sage",
        },
        {
          label: "Sign-in method",
          value: "Staff PIN",
          hint: "A PIN that’s personal to you",
          icon: KeyRound,
          tone: "sand",
        },
        {
          label: "Workspace",
          value: "Connected",
          hint: "Your current session is verified",
          icon: ShieldCheck,
          tone: "lavender",
        },
      ];
  return (
    <div className="page-enter">
      <div className="page-heading">
        <div>
          <span className="eyebrow">YOUR DAILY STARTING POINT</span>
          <h1>Workspace overview</h1>
          <p>A clear view of your people and your account.</p>
        </div>
        <span className="date-chip">
          <CalendarDays size={16} />
          {date}
        </span>
      </div>
      <section className="welcome-banner">
        <div>
          <span className="welcome-kicker">
            <span />
            ALL SET FOR YOUR NEXT SERVICE
          </span>
          <h2>
            Hello, {user.first_name || user.username}
            <span className="welcome-period">.</span>
          </h2>
          <p>
            {owner
              ? "Your team’s access starts with you. Keep everyone ready to sign in."
              : "You’re signed in and ready. Your account is right where you need it."}
          </p>
          <Link to={owner ? "/staff" : "/profile"} className="welcome-link">
            {owner ? "Manage your team" : "View your profile"}{" "}
            <ArrowRight size={17} />
          </Link>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="welcome-circle">
            <ShieldCheck size={47} strokeWidth={1.1} />
          </div>
          <span className="welcome-check">
            <Check size={17} />
          </span>
          <span className="art-dot" />
        </div>
      </section>
      <nav className="workspace-shortcuts" aria-label="Restaurant workspace">
        <Link to="/restaurant">
          <span>Restaurant profile</span>
          <ArrowUpRight size={18} />
        </Link>
        <Link to="/menu">
          <span>Menu catalogue</span>
          <ArrowUpRight size={18} />
        </Link>
        <Link to="/tables">
          <span>Tables & seating</span>
          <ArrowUpRight size={18} />
        </Link>
      </nav>
      <section className="stats-grid" aria-label="Workspace summary">
        {stats.map(({ label, value, hint, icon: Icon, tone }) => (
          <article className="stat-card" key={label}>
            <div className="stat-top">
              <span>{label}</span>
              <span className={`stat-icon tone-${tone}`}>
                <Icon size={18} />
              </span>
            </div>
            <strong className={value === undefined ? "stat-pending" : ""}>
              {value ?? "—"}
            </strong>
            <p>{hint}</p>
          </article>
        ))}
      </section>
      <div className="overview-bottom">
        <section className="card team-overview">
          <div className="section-header">
            <div>
              <h2>{owner ? "Your team, at a glance" : "Your workspace"}</h2>
              <p>
                {owner
                  ? "The people who make it happen."
                  : "Everything you need to manage your own access."}
              </p>
            </div>
            {owner && (
              <Link to="/staff" className="text-link">
                View team <ArrowUpRight size={15} />
              </Link>
            )}
          </div>
          {owner ? (
            <>
              {team.error && (
                <div className="p-5">
                  <Notice>
                    {team.error}
                    <Button variant="ghost" onClick={() => void team.load()}>
                      Try again
                    </Button>
                  </Notice>
                </div>
              )}
              {team.loading && !team.staff ? (
                <div
                  className="skeleton-list"
                  aria-label="Loading team"
                  aria-busy="true"
                >
                  {[1, 2, 3].map((row) => (
                    <div className="skeleton-row" key={row}>
                      <span />
                      <div />
                      <i />
                    </div>
                  ))}
                </div>
              ) : team.staff?.length ? (
                <div className="overview-members">
                  {team.staff.slice(0, 4).map((member) => (
                    <div className="overview-member" key={member.id}>
                      <Avatar user={member} />
                      <div className="member-name">
                        <strong>{displayName(member)}</strong>
                        <small>{roleLabel(member.role)}</small>
                      </div>
                      <StatusBadge user={member} />
                    </div>
                  ))}
                </div>
              ) : (
                !team.error && (
                  <div className="empty-state">
                    <span className="empty-icon">
                      <UsersRound size={28} />
                    </span>
                    <h3>Great teams start with one.</h3>
                    <p>
                      Add your first staff member and give them a place in your
                      workspace.
                    </p>
                    <Link to="/staff?create=1" className="btn btn-primary">
                      Add a staff member <ArrowRight size={16} />
                    </Link>
                  </div>
                )
              )}
            </>
          ) : (
            <div className="staff-welcome">
              <div className="tone-sage staff-welcome-icon">
                <ShieldCheck size={30} />
              </div>
              <h3>You’re in the right place.</h3>
              <p>
                Your {roleLabel(user.role).toLowerCase()} account is active.
                Keep your PIN private and sign out when you’re done on a shared
                device.
              </p>
              <Link to="/profile" className="text-link">
                Manage your account <ArrowRight size={16} />
              </Link>
            </div>
          )}
        </section>
        <section className="card account-overview">
          <span className="eyebrow">SIGNED IN AS</span>
          <div className="account-overview-user">
            <Avatar user={user} size="large" />
            <h2>{displayName(user)}</h2>
            <span>@{user.username}</span>
            <RoleBadge user={user} />
          </div>
          <div className="account-details">
            <div>
              <span>Account status</span>
              <span className="text-green flex items-center gap-1.5">
                <span className="tiny-dot" />
                Active
              </span>
            </div>
            <div>
              <span>Sign-in method</span>
              <strong>{owner ? "Password" : "Staff PIN"}</strong>
            </div>
          </div>
          <Link to="/profile" className="btn btn-secondary w-full">
            My profile & security <ArrowUpRight size={16} />
          </Link>
        </section>
      </div>
      <div className="dashboard-note">
        <ShieldCheck size={17} />
        <span>
          Your workspace reflects your assigned role. Need different access?{" "}
          {owner
            ? "Staff roles are set when you create an account."
            : "Speak with your Owner."}
        </span>
      </div>
    </div>
  );
}
