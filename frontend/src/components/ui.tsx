import { useEffect, useId, useRef, useState } from "react";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
} from "react";
import {
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  LoaderCircle,
  Utensils,
  X,
} from "lucide-react";
import type { ApiError } from "../lib/api";
import type { User } from "../types";
import { initials, roleLabel } from "../types";

export function Brand({ dark = false }: { dark?: boolean }) {
  return (
    <span className={`brand ${dark ? "brand-dark" : ""}`}>
      <span className="brand-mark">
        <Utensils size={21} strokeWidth={1.7} />
      </span>
      <span>
        rms<span className="brand-period">.</span>
      </span>
    </span>
  );
}
export function Button({
  children,
  variant = "primary",
  loading = false,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={`btn btn-${variant} ${className}`}
      aria-busy={loading || undefined}
    >
      {loading && (
        <LoaderCircle className="animate-spin" size={17} aria-hidden="true" />
      )}
      {children}
    </button>
  );
}
export function Field({
  label,
  hint,
  error,
  id,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
}) {
  const generated = useId();
  const inputId = id || generated;
  return (
    <div className="field">
      <label htmlFor={inputId}>{label}</label>
      <input
        {...props}
        id={inputId}
        className={`input ${props.className || ""}`}
        aria-invalid={!!error || undefined}
        aria-describedby={
          error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
        }
      />
      {error && (
        <span className="field-error" id={`${inputId}-error`}>
          {error}
        </span>
      )}
      {!error && hint && (
        <span className="field-hint" id={`${inputId}-hint`}>
          {hint}
        </span>
      )}
    </div>
  );
}
export function SecretField({
  label,
  hint,
  error,
  pin = false,
  pinLength = 4,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
  pin?: boolean;
  pinLength?: 4 | 6;
}) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="secret-input">
        <input
          {...props}
          id={id}
          className={`input ${pin ? "pin-input" : ""}`}
          type={visible ? "text" : "password"}
          inputMode={pin ? "numeric" : undefined}
          maxLength={pin ? pinLength : 1024}
          minLength={pin ? pinLength : props.minLength}
          pattern={pin ? `[0-9]{${pinLength}}` : undefined}
          aria-invalid={!!error || undefined}
          aria-describedby={
            error ? `${id}-error` : hint ? `${id}-hint` : undefined
          }
        />
        <button
          type="button"
          className="reveal-button"
          aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      </div>
      {error && (
        <span className="field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
      {!error && hint && (
        <span className="field-hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  );
}
export function Notice({
  children,
  kind = "error",
}: {
  children: ReactNode;
  kind?: "error" | "success" | "info";
}) {
  return (
    <div
      className={`notice notice-${kind}`}
      role={kind === "error" ? "alert" : "status"}
    >
      {kind === "success" ? (
        <CheckCircle2 size={19} aria-hidden="true" />
      ) : (
        <AlertCircle size={19} aria-hidden="true" />
      )}
      <div>{children}</div>
    </div>
  );
}
export function ActionError({
  error,
  remaining = 0,
}: {
  error: ApiError | null;
  remaining?: number;
}) {
  if (!error) return null;
  return (
    <Notice>
      {error.message}
      {remaining > 0 && (
        <span className="block mt-1 font-semibold">
          Try again in {Math.floor(remaining / 60)}:
          {String(remaining % 60).padStart(2, "0")}.
        </span>
      )}
    </Notice>
  );
}
export function Avatar({
  user,
  size = "normal",
}: {
  user: User;
  size?: "normal" | "large";
}) {
  return (
    <span
      className={`avatar avatar-${size} avatar-${user.role}`}
      aria-hidden="true"
    >
      {initials(user)}
    </span>
  );
}
export function RoleBadge({ user }: { user: User }) {
  return (
    <span className={`role-badge role-${user.role}`}>
      {roleLabel(user.role)}
    </span>
  );
}
export function StatusBadge({ user }: { user: User }) {
  const status = !user.is_active
    ? "inactive"
    : user.must_change_pin
      ? "pending"
      : "active";
  return (
    <span className={`status-badge status-${status}`}>
      <span />
      {status === "pending"
        ? "PIN change needed"
        : status === "active"
          ? "Active"
          : "Inactive"}
    </span>
  );
}
export function LoadingPage({
  message = "Opening your workspace…",
}: {
  message?: string;
}) {
  return (
    <div className="loading-page">
      <Brand />
      <LoaderCircle className="animate-spin text-green" size={25} />
      <p>{message}</p>
    </div>
  );
}
export function Dialog({
  title,
  children,
  onClose,
  busy = false,
  className = "",
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const heading = useId();
  useEffect(() => {
    const element = ref.current;
    const trigger = document.activeElement;
    element?.showModal();
    return () => {
      element?.close();
      if (trigger instanceof HTMLElement && trigger.isConnected) {
        trigger.focus({ preventScroll: true });
      }
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={heading}
      className={`app-dialog ${className}`}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="dialog-header">
        <h2 id={heading}>{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Close dialog"
          disabled={busy}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
