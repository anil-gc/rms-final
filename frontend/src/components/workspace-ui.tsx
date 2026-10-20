import { useId } from "react";
import type { ReactNode, TextareaHTMLAttributes } from "react";
import { LoaderCircle, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { Link } from "react-router";
import type { ApiError } from "../lib/api";
import { Button, Notice } from "./ui";

export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
export function TextArea({
  label,
  error,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  error?: string;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <textarea
        {...props}
        id={id}
        className="input textarea"
        aria-invalid={!!error || undefined}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error && (
        <span className="field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
    </div>
  );
}
export function Toggle({
  label,
  checked,
  onChange,
  disabled = false,
  hint,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  hint?: string;
}) {
  const hintId = useId();
  return (
    <label className={`workspace-toggle ${disabled ? "toggle-disabled" : ""}`}>
      <input
        type="checkbox"
        aria-label={label}
        aria-describedby={hint ? hintId : undefined}
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span className="toggle-track" aria-hidden="true" />
      <span>
        <strong>{label}</strong>
        {hint && <small id={hintId}>{hint}</small>}
      </span>
    </label>
  );
}
export function RecordBadge({
  active,
  children,
}: {
  active: boolean;
  children: ReactNode;
}) {
  return (
    <span
      className={`record-badge ${active ? "record-active" : "record-muted"}`}
    >
      <span />
      {children}
    </span>
  );
}
export function ResourceStatus({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: ApiError | null;
  retry: () => void;
}) {
  if (error)
    return (
      <Notice>
        {error.message}
        <Button variant="ghost" onClick={retry}>
          <RefreshCw size={15} />
          Try again
        </Button>
      </Notice>
    );
  if (loading)
    return (
      <div className="resource-loading" role="status">
        <LoaderCircle size={20} className="animate-spin" />
        Loading workspace data…
      </div>
    );
  return null;
}
export function ReadOnlyNote() {
  return (
    <div className="workspace-note">
      <ShieldCheck size={17} />
      <span>
        You have read-only access. Your Owner or Manager manages these details.
      </span>
    </div>
  );
}
export function SetupNotice() {
  return (
    <Notice kind="info">
      Set up your restaurant profile before adding menu categories or tables.{" "}
      <Link className="text-link" to="/restaurant">
        Open restaurant profile
      </Link>
    </Notice>
  );
}
export function EmptyRecords({
  title,
  description,
  action,
  onAction,
}: {
  title: string;
  description: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{description}</p>
      {action && onAction && (
        <Button onClick={onAction}>
          <Plus size={16} />
          {action}
        </Button>
      )}
    </div>
  );
}
