import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  KeyRound,
  Plus,
  Search,
  ShieldCheck,
  UserRoundCheck,
  UserRoundMinus,
  UsersRound,
} from "lucide-react";
import { useSearchParams } from "react-router";
import { api } from "../lib/api";
import { useStaff } from "../hooks/useStaff";
import { useAction } from "../hooks/useAction";
import {
  ActionError,
  Avatar,
  Button,
  Dialog,
  Field,
  Notice,
  RoleBadge,
  SecretField,
  StatusBadge,
} from "../components/ui";
import { displayName, roleLabel, staffRoles } from "../types";
import type { StaffRole, User } from "../types";

type StaffDialog =
  { kind: "create" } | { kind: "reset" | "state"; member: User };

function StaffMutationDialog({
  dialog,
  close,
  saved,
}: {
  dialog: StaffDialog;
  close: () => void;
  saved: (message: string) => void;
}) {
  const [username, setUsername] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState<StaffRole>("waiter");
  const [pin, setPin] = useState("");
  const [password, setPassword] = useState("");
  const action = useAction();
  const title =
    dialog.kind === "create"
      ? "Add a staff member"
      : dialog.kind === "reset"
        ? "Reset staff PIN"
        : dialog.member.is_active
          ? "Deactivate account"
          : "Reactivate account";
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await action.run(async () => {
      if (dialog.kind === "create")
        return api.createStaff({
          username: username.trim(),
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          role,
          pin,
          owner_password: password,
        });
      if (dialog.kind === "reset")
        return api.resetPin(dialog.member.id, pin, password);
      return api.setActive(
        dialog.member.id,
        !dialog.member.is_active,
        password,
      );
    });
    setPassword("");
    setPin("");
    if (result)
      saved(
        dialog.kind === "create"
          ? `${displayName(result)} has been added. Share their temporary PIN privately.`
          : dialog.kind === "reset"
            ? `PIN reset for ${displayName(result)}. They must change it after signing in.`
            : `${displayName(result)}’s account is now ${result.is_active ? "active" : "inactive"}.`,
      );
  }
  return (
    <Dialog title={title} onClose={close} busy={action.pending}>
      <form onSubmit={submit} className="dialog-body form-stack">
        <p className="text-muted">
          {dialog.kind === "create"
            ? "Give someone on your team their own secure sign-in."
            : dialog.kind === "reset"
              ? `Set a new temporary PIN for ${displayName(dialog.member)}. Their other sessions will be signed out.`
              : dialog.member.is_active
                ? `${displayName(dialog.member)} will lose sign-in access and their current sessions will end. You can reactivate this account later.`
                : `Restore sign-in access for ${displayName(dialog.member)}. They’ll need to sign in again.`}
        </p>
        <ActionError error={action.error} remaining={action.remaining} />
        {dialog.kind === "create" && (
          <>
            <div className="form-columns">
              <Field
                label="First name"
                name="first_name"
                autoComplete="off"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                maxLength={150}
                error={action.error?.fields.first_name}
              />
              <Field
                label="Last name"
                name="last_name"
                autoComplete="off"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                maxLength={150}
                error={action.error?.fields.last_name}
              />
            </div>
            <Field
              label="Staff username"
              name="username"
              autoComplete="off"
              placeholder="e.g. aayush"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              maxLength={150}
              error={action.error?.fields.username}
              hint="Their unique name for signing in. Usernames are case-sensitive."
            />
            <div className="field">
              <label htmlFor="staff-role">Role</label>
              <select
                id="staff-role"
                className="input"
                value={role}
                onChange={(e) => setRole(e.target.value as StaffRole)}
              >
                {staffRoles.map((item) => (
                  <option key={item} value={item}>
                    {roleLabel(item)}
                  </option>
                ))}
              </select>
              <span className="field-hint">
                Choose the role this person needs. Owner accounts can’t be
                created here.
              </span>
            </div>
          </>
        )}
        {dialog.kind !== "state" && (
          <SecretField
            label="Temporary PIN"
            name="new_pin"
            pin
            required
            autoComplete="new-password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            hint="Six digits. Avoid repeated or sequential numbers. They must change this PIN on first sign-in."
            error={action.error?.fields.pin || action.error?.fields.new_pin}
          />
        )}
        <div className="owner-confirmation">
          <div className="owner-confirmation-label">
            <ShieldCheck size={17} />
            Confirm it’s you
          </div>
          <SecretField
            label="Your Owner password"
            name="owner_password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={action.error?.fields.owner_password}
          />
        </div>
        <div className="dialog-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={close}
            disabled={action.pending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant={
              dialog.kind === "state" && dialog.member.is_active
                ? "danger"
                : "primary"
            }
            loading={action.pending}
            disabled={action.remaining > 0}
          >
            {dialog.kind === "create"
              ? "Add staff member"
              : dialog.kind === "reset"
                ? "Reset PIN"
                : dialog.member.is_active
                  ? "Deactivate account"
                  : "Reactivate account"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export function StaffPage() {
  const team = useStaff();
  const [query, setQuery] = useState("");
  const [filterRole, setFilterRole] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [dialog, setDialog] = useState<StaffDialog | null>(null);
  const [notice, setNotice] = useState("");
  const [params, setParams] = useSearchParams();
  useEffect(() => {
    if (params.get("create") === "1") {
      setDialog({ kind: "create" });
      setParams({}, { replace: true });
    }
  }, [params, setParams]);
  const members = (team.staff || []).filter((member) => {
    const matches = `${displayName(member)} ${member.username}`
      .toLowerCase()
      .includes(query.toLowerCase());
    return (
      matches &&
      (filterRole === "all" || member.role === filterRole) &&
      (filterStatus === "all" ||
        (filterStatus === "active" ? member.is_active : !member.is_active))
    );
  });
  const controls = (member: User) => (
    <div className="staff-row-actions">
      <button
        className="row-action"
        onClick={() => setDialog({ kind: "reset", member })}
        aria-label={`Reset PIN for ${displayName(member)}`}
      >
        <KeyRound size={15} />
        <span>Reset PIN</span>
      </button>
      <button
        className={`row-action ${member.is_active ? "row-action-danger" : ""}`}
        onClick={() => setDialog({ kind: "state", member })}
        aria-label={`${member.is_active ? "Deactivate" : "Reactivate"} ${displayName(member)}`}
      >
        {member.is_active ? (
          <UserRoundMinus size={16} />
        ) : (
          <UserRoundCheck size={16} />
        )}
        <span>{member.is_active ? "Deactivate" : "Reactivate"}</span>
      </button>
    </div>
  );
  return (
    <div className="page-enter">
      <div className="page-heading">
        <div>
          <span className="eyebrow">PEOPLE MAKE THE DIFFERENCE</span>
          <h1>Staff management</h1>
          <p>Your people. The right role. A secure way in.</p>
        </div>
        <Button
          onClick={() => {
            setNotice("");
            setDialog({ kind: "create" });
          }}
        >
          <Plus size={18} />
          Add staff member
        </Button>
      </div>
      {notice && (
        <div className="mb-6">
          <Notice kind="success">{notice}</Notice>
        </div>
      )}
      <div className="team-summary">
        <span>
          <UsersRound size={18} />
          <strong>{team.staff?.length ?? "—"}</strong>team members
        </span>
        <span>
          <span className="tiny-dot" />
          <strong>
            {team.staff?.filter((member) => member.is_active).length ?? "—"}
          </strong>
          active accounts
        </span>
        <span className="team-summary-note">
          <ShieldCheck size={15} />
          Only you can manage staff access
        </span>
      </div>
      <section className="card team-card">
        <div className="team-toolbar">
          <div className="search-input">
            <Search size={18} />
            <input
              aria-label="Search staff"
              placeholder="Search name or username…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="team-filters">
            <select
              className="input filter-select"
              aria-label="Filter by role"
              value={filterRole}
              onChange={(e) => setFilterRole(e.target.value)}
            >
              <option value="all">All roles</option>
              {staffRoles.map((item) => (
                <option value={item} key={item}>
                  {roleLabel(item)}
                </option>
              ))}
            </select>
            <select
              className="input filter-select"
              aria-label="Filter by account status"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
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
            aria-label="Loading staff"
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
        ) : members.length ? (
          <>
            <div className="desktop-team">
              <table className="team-table">
                <thead>
                  <tr>
                    <th>TEAM MEMBER</th>
                    <th>ROLE</th>
                    <th>ACCOUNT ACCESS</th>
                    <th className="text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.id}>
                      <td>
                        <div className="flex items-center gap-3">
                          <Avatar user={member} />
                          <div className="member-name">
                            <strong>{displayName(member)}</strong>
                            <small>@{member.username}</small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <RoleBadge user={member} />
                      </td>
                      <td>
                        <StatusBadge user={member} />
                      </td>
                      <td>{controls(member)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mobile-team">
              {members.map((member) => (
                <article key={member.id} className="mobile-member">
                  <div className="flex items-center gap-3">
                    <Avatar user={member} />
                    <div className="member-name">
                      <strong>{displayName(member)}</strong>
                      <small>@{member.username}</small>
                    </div>
                    <RoleBadge user={member} />
                  </div>
                  <StatusBadge user={member} />
                  {controls(member)}
                </article>
              ))}
            </div>
            <div className="team-table-footer">
              Showing {members.length} of {team.staff?.length} staff members
              {team.loading && <span role="status">Refreshing…</span>}
            </div>
          </>
        ) : (
          !team.error && (
            <div className="empty-state">
              <span className="empty-icon">
                <UsersRound size={28} />
              </span>
              <h3>
                {team.staff?.length
                  ? "No one matches just yet."
                  : "Make room for your team."}
              </h3>
              <p>
                {team.staff?.length
                  ? "Try a different name or clear your filters."
                  : "Add a staff member to create their personal sign-in."}
              </p>
              {team.staff?.length ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setQuery("");
                    setFilterRole("all");
                    setFilterStatus("all");
                  }}
                >
                  Clear filters
                </Button>
              ) : (
                <Button onClick={() => setDialog({ kind: "create" })}>
                  <Plus size={16} />
                  Add your first staff member
                </Button>
              )}
            </div>
          )
        )}
      </section>
      <div className="dashboard-note">
        <KeyRound size={17} />
        <span>
          New and reset PINs are temporary. Staff must change them before
          entering the workspace.
        </span>
      </div>
      {dialog && (
        <StaffMutationDialog
          dialog={dialog}
          close={() => setDialog(null)}
          saved={(message) => {
            setDialog(null);
            setNotice(message);
            void team.load();
          }}
        />
      )}
    </div>
  );
}
