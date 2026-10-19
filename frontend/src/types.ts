export const staffRoles = ["manager", "cashier", "waiter", "chef"] as const;
export type StaffRole = (typeof staffRoles)[number];
export type Role = "owner" | StaffRole;
export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_active: boolean;
  must_change_pin: boolean;
}
export interface LoginResponse {
  user: User;
  csrf_token: string;
}
export interface StaffInput {
  username: string;
  first_name: string;
  last_name: string;
  role: StaffRole;
  pin: string;
  owner_password: string;
}
export const roleLabel = (role: Role) =>
  role.charAt(0).toUpperCase() + role.slice(1);
export const displayName = (user: User) =>
  `${user.first_name} ${user.last_name}`.trim() || user.username;
export const initials = (user: User) =>
  displayName(user)
    .split(/[\s._-]+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
