import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, ApiError, invalidateCsrf } from "../lib/api";
import type { User } from "../types";
import { AuthContext } from "./auth-context";
import type { AuthStatus } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [loginPath, setLoginPath] = useState<"/login/owner" | "/login/staff">(
    "/login/owner",
  );
  const channel = useRef<BroadcastChannel | null>(null);
  const revision = useRef(0);
  const mounted = useRef(false);
  const cancelPending = useCallback(() => {
    revision.current++;
  }, []);

  const refresh = useCallback(async () => {
    const current = ++revision.current;
    try {
      const profile = await api.me();
      if (mounted.current && current === revision.current) {
        setUser(profile);
        setStatus("authenticated");
        setLoginPath(
          profile.role === "owner" ? "/login/owner" : "/login/staff",
        );
      }
    } catch (error) {
      if (!mounted.current || current !== revision.current) return;
      if (
        error instanceof ApiError &&
        (error.status === 401 || error.status === 403)
      ) {
        invalidateCsrf();
        setUser(null);
        setStatus("anonymous");
      } else {
        // Network errors must not be presented as successful logout.
        setStatus("unavailable");
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    const check = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    const otherTab = () => {
      invalidateCsrf();
      void refresh();
    };
    window.addEventListener("focus", check);
    window.addEventListener("rms:check-session", check);
    document.addEventListener("visibilitychange", check);
    const timer = window.setInterval(check, 60_000);
    if (typeof BroadcastChannel !== "undefined") {
      channel.current = new BroadcastChannel("rms-account-session");
      channel.current.onmessage = otherTab;
    }
    return () => {
      mounted.current = false;
      cancelPending();
      clearInterval(timer);
      channel.current?.close();
      channel.current = null;
      window.removeEventListener("focus", check);
      window.removeEventListener("rms:check-session", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [refresh, cancelPending]);

  const updateUser = useCallback((profile: User) => {
    revision.current++;
    setUser(profile);
    setStatus("authenticated");
    setLoginPath(profile.role === "owner" ? "/login/owner" : "/login/staff");
    channel.current?.postMessage("changed");
  }, []);
  async function loginOwner(username: string, password: string) {
    const response = await api.ownerLogin(username, password);
    updateUser(response.user);
    return response.user;
  }
  async function loginStaff(username: string, pin: string) {
    const response = await api.staffLogin(username, pin);
    updateUser(response.user);
    return response.user;
  }
  async function logout() {
    await api.logout();
    revision.current++;
    invalidateCsrf();
    setUser(null);
    setStatus("anonymous");
    channel.current?.postMessage("changed");
  }
  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        loginPath,
        refresh,
        loginOwner,
        loginStaff,
        logout,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
