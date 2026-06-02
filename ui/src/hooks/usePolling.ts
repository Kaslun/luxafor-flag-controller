import { useEffect, useRef, useState } from "react";

/** Poll an async fetcher on an interval. Returns the latest value, any
 *  error, and a manual refresh. The first load happens immediately. */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number
): { data: T | null; error: string | null; refresh: () => void } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = () => {
    fetcherRef
      .current()
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    run();
    const id = setInterval(run, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return { data, error, refresh: run };
}
