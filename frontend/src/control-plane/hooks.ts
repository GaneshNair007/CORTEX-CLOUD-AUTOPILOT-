import { useCallback, useEffect, useRef, useState } from "react";

export function useResource<T>(
  load: (signal: AbortSignal) => Promise<T>,
  interval = 15000,
) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<number>();
  const [revision, setRevision] = useState(0);
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      setLoading(true);
      try {
        const result = await load(controller.signal);
        if (!stopped) {
          setData(result);
          setUpdatedAt(Date.now());
          setError("");
        }
      } catch (e) {
        if (!stopped)
          setError(e instanceof Error ? e.message : "Request failed.");
      } finally {
        if (!stopped) {
          setLoading(false);
          if (interval) timer = setTimeout(poll, interval);
        }
      }
    }
    void poll();
    return () => {
      stopped = true;
      controller.abort();
      clearTimeout(timer);
    };
  }, [load, interval, revision]);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 5000);
    return () => clearInterval(timer);
  }, []);
  const refresh = useCallback(() => setRevision((n) => n + 1), []);
  return {
    data,
    error,
    loading,
    updatedAt,
    refresh,
    stale: Boolean(updatedAt && (error || clock - updatedAt > 60000)),
  };
}
export function useAction() {
  const busy = useRef(false);
  const mounted = useRef(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function run<T>(action: () => Promise<T>): Promise<T | undefined> {
    if (busy.current) return;
    busy.current = true;
    setPending(true);
    setError("");
    try {
      return await action();
    } catch (e) {
      if (mounted.current)
        setError(e instanceof Error ? e.message : "Request failed.");
    } finally {
      busy.current = false;
      if (mounted.current) setPending(false);
    }
  }
  return { pending, error, run };
}
