import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { User } from "../types";

export function useStaff(enabled = true) {
  const [staff, setStaff] = useState<User[] | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const version = useRef(0);
  const cancelPending = useCallback(() => {
    version.current++;
  }, []);
  const load = useCallback(async () => {
    if (!enabled) return;
    const current = ++version.current;
    setLoading(true);
    setError(null);
    try {
      const result = await api.staff();
      if (current === version.current) setStaff(result);
    } catch (cause) {
      if (current === version.current)
        setError(
          cause instanceof ApiError
            ? cause.message
            : "Could not load your team.",
        );
    } finally {
      if (current === version.current) setLoading(false);
    }
  }, [enabled]);
  useEffect(() => {
    void load();
    return cancelPending;
  }, [load, cancelPending]);
  return { staff, loading, error, load };
}
