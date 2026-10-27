import { useState } from "react";
import type { FormEvent } from "react";
import {
  ArrowRight,
  Fingerprint,
  KeyRound,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { api, ApiError } from "../lib/api";
import { useAction } from "../hooks/useAction";
import {
  ActionError,
  Avatar,
  Button,
  Notice,
  RoleBadge,
  SecretField,
} from "../components/ui";
import { displayName, roleLabel } from "../types";

export function CredentialForm({
  required = false,
  onComplete,
}: {
  required?: boolean;
  onComplete?: () => void;
}) {
  const { user, updateUser } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [success, setSuccess] = useState(false);
  const [legacyPin, setLegacyPin] = useState(false);
  const action = useAction();
  if (!user) return null;
  const owner = user.role === "owner";
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(false);
    if (next !== confirm) {
      action.setError(
        new ApiError(
          `The new ${owner ? "passwords" : "PINs"} don’t match.`,
          400,
        ),
      );
      return;
    }
    const profile = await action.run(() =>
      owner ? api.changePassword(current, next) : api.changePin(current, next),
    );
    setCurrent("");
    setNext("");
    setConfirm("");
    if (profile) {
      setLegacyPin(false);
      updateUser(profile);
      setSuccess(true);
      onComplete?.();
    }
  }
  return (
    <form onSubmit={submit} className="form-stack">
      <ActionError error={action.error} remaining={action.remaining} />
      {success && (
        <Notice kind="success">
          Your {owner ? "password" : "PIN"} has been updated. Your other
          sessions have been signed out.
        </Notice>
      )}
      <SecretField
        label={
          owner
            ? "Current password"
            : required
              ? "Temporary PIN"
              : "Current PIN"
        }
        name={owner ? "current_password" : "current_pin"}
        pin={!owner}
        pinLength={legacyPin ? 6 : 4}
        required
        autoComplete="current-password"
        value={current}
        onChange={(e) => setCurrent(e.target.value)}
        error={action.error?.fields[owner ? "current_password" : "current_pin"]}
      />
      {!owner && (
        <label className="field-hint">
          <input
            type="checkbox"
            checked={legacyPin}
            onChange={(event) => {
              setLegacyPin(event.target.checked);
              setCurrent("");
            }}
          />{" "}
          My current or temporary PIN still has 6 digits
        </label>
      )}
      <SecretField
        label={owner ? "New password" : "New PIN"}
        name={owner ? "new_password" : "new_pin"}
        pin={!owner}
        required
        autoComplete="new-password"
        minLength={owner ? 15 : 4}
        value={next}
        onChange={(e) => setNext(e.target.value)}
        hint={
          owner
            ? "At least 15 characters. Choose a unique password you don’t use elsewhere."
            : "Exactly four digits, different from your current PIN. Avoid obvious sequences or repeated numbers."
        }
        error={action.error?.fields[owner ? "new_password" : "new_pin"]}
      />
      <SecretField
        label={owner ? "Confirm new password" : "Confirm new PIN"}
        name="confirm"
        pin={!owner}
        required
        autoComplete="new-password"
        minLength={owner ? 15 : 4}
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />
      <Button
        type="submit"
        className={required ? "w-full" : "self-start"}
        loading={action.pending}
        disabled={action.remaining > 0}
      >
        {required
          ? "Set my PIN & continue"
          : owner
            ? "Update password"
            : "Update PIN"}
        <ArrowRight size={16} />
      </Button>
    </form>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div className="page-enter">
      <div className="page-heading">
        <div>
          <span className="eyebrow">A SPACE THAT’S YOURS</span>
          <h1>My profile</h1>
          <p>Your account details and the keys to your workspace.</p>
        </div>
        <span className="date-chip">
          <ShieldCheck size={16} />
          Account active
        </span>
      </div>
      <div className="profile-grid">
        <section className="card profile-card">
          <div className="profile-cover" />
          <div className="profile-summary">
            <Avatar user={user} size="large" />
            <h2>{displayName(user)}</h2>
            <p>@{user.username}</p>
            <RoleBadge user={user} />
          </div>
          <dl className="profile-details">
            <div>
              <dt>Username</dt>
              <dd>{user.username}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>{roleLabel(user.role)}</dd>
            </div>
            <div>
              <dt>Sign-in method</dt>
              <dd>{user.role === "owner" ? "Owner password" : "Staff PIN"}</dd>
            </div>
            <div>
              <dt>Account status</dt>
              <dd className="text-green">Active</dd>
            </div>
          </dl>
          <div className="profile-note">
            <UserRound size={17} />
            <p>
              {user.role === "owner"
                ? "You manage staff accounts and their access to this workspace."
                : "Your Owner manages your account details and role."}
            </p>
          </div>
        </section>
        <section className="card security-card">
          <div className="security-heading">
            <span className="security-icon">
              <Fingerprint size={24} />
            </span>
            <div>
              <h2>
                {user.role === "owner"
                  ? "Change your password"
                  : "Change your PIN"}
              </h2>
              <p>Keep your access personal and secure.</p>
            </div>
          </div>
          <CredentialForm />
          <div className="security-footer">
            <KeyRound size={17} />
            <p>
              Changing your credentials signs out your other sessions. This
              device stays signed in.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
