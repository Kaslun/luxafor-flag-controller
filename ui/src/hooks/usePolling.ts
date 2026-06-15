import { useEffect, useRef, useState } from "react";

/** Poll an async fetcher on an interval. Returns the latest value, any
 *  error, a consecutive-failure count, and a manual refresh. The first load
 *  happens immediately. */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number
): { data: T | null; error: string | null; failures: number; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failures, setFailures] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = () => {
    fetcherRef
      .current()
      .then((d) => {
        setData(d);
        setError(null);
        setFailures(0);
      })
      .catch((e) => {
        setError(String(e));
        setFailures((n) => n + 1);
      });
  };

  useEffect(() => {
    run();
    const id = setInterval(run, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return { data, error, failures, refresh: run };
}
