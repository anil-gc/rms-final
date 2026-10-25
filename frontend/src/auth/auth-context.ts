import { createContext, useContext } from "react";
import type { User } from "../types";

export type AuthStatus =
  "loading" | "authenticated" | "anonymous" | "unavailable";
export interface AuthValue {
  user: User | null;
  status: AuthStatus;
  loginPath: "/login/owner" | "/login/staff";
  refresh: () => Promise<void>;
  loginOwner: (username: string, password: string) => Promise<User>;
  loginStaff: (username: string, pin: string) => Promise<User>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}
export const AuthContext = createContext<AuthValue | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
