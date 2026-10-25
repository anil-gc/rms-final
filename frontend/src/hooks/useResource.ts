import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../lib/api";

export function useResource<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const revision = useRef(0);
  const cancel = useCallback(() => {
    revision.current++;
  }, []);
  const load = useCallback(async () => {
    const current = ++revision.current;
    setLoading(true);
    setError(null);
    try {
      const value = await loader();
      if (current === revision.current) setData(value);
    } catch (cause) {
      if (current === revision.current)
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError("Could not load this page. Please try again.", 0),
        );
    } finally {
      if (current === revision.current) setLoading(false);
    }
  }, [loader]);
  useEffect(() => {
    void load();
    return cancel;
  }, [load, cancel]);
  return { data, loading, error, load };
}
