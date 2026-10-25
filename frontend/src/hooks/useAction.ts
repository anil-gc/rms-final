import { useEffect, useRef, useState } from "react";
import { ApiError } from "../lib/api";

export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [remaining, setRemaining] = useState(0);
  const lock = useRef(false);
  useEffect(() => {
    if (!error?.retryAfter) {
      setRemaining(0);
      return;
    }
    const until = Date.now() + error.retryAfter * 1000;
    const tick = () =>
      setRemaining(Math.max(0, Math.ceil((until - Date.now()) / 1000)));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [error]);
  async function run<T>(operation: () => Promise<T>): Promise<T | undefined> {
    if (lock.current || remaining > 0) return;
    lock.current = true;
    setPending(true);
    setError(null);
    try {
      return await operation();
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause
          : new ApiError("Something went wrong. Please try again.", 0),
      );
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return { run, pending, error, setError, remaining };
}
