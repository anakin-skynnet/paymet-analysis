import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

const STORAGE_KEY = "payment-analysis-mock-data";

/**
 * Default is false: UI uses real Databricks data. Only when the user has
 * explicitly turned the toggle ON is this true (stored in localStorage).
 */
function loadMockSetting(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function saveMockSetting(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, String(enabled));
  } catch {
    // ignore
  }
}

interface MockDataContextValue {
  /** When true, API calls include X-Mock-Data header and the backend returns mock data */
  mockEnabled: boolean;
  setMockEnabled: (enabled: boolean) => void;
}

const MockDataContext = createContext<MockDataContextValue | null>(null);

/**
 * Global fetch interceptor: when mock mode is ON, injects the
 * `X-Mock-Data: true` header into every `/api/` request so the
 * backend returns mock data instead of querying Databricks.
 */
function installFetchInterceptor(enabled: boolean) {
  // Store the *original* native fetch once (on first call)
  const nativeFetch =
    (window as unknown as { __nativeFetch?: typeof fetch }).__nativeFetch ??
    window.fetch.bind(window);
  (window as unknown as { __nativeFetch: typeof fetch }).__nativeFetch =
    nativeFetch;

  if (enabled) {
    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input instanceof Request
              ? input.url
              : String(input);

      // Only inject header for our own API calls
      if (url.startsWith("/api/")) {
        const headers = new Headers(init?.headers);
        headers.set("X-Mock-Data", "true");
        return nativeFetch(input, { ...init, headers });
      }
      return nativeFetch(input, init);
    };
  } else {
    // Restore original fetch
    window.fetch = nativeFetch;
  }
}

export function MockDataProvider({ children }: { children: ReactNode }) {
  const [mockEnabled, setMockState] = useState(loadMockSetting);
  const queryClient = useQueryClient();
  const isFirstRender = useRef(true);

  const setMockEnabled = useCallback((enabled: boolean) => {
    setMockState(enabled);
    saveMockSetting(enabled);
  }, []);

  // Install / uninstall the fetch interceptor whenever the flag changes
  useEffect(() => {
    installFetchInterceptor(mockEnabled);
    return () => installFetchInterceptor(false);
  }, [mockEnabled]);

  // Invalidate all queries when mock mode toggles so the UI refetches with the new header
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    queryClient.invalidateQueries();
  }, [mockEnabled, queryClient]);

  const value = useMemo(
    () => ({ mockEnabled, setMockEnabled }),
    [mockEnabled, setMockEnabled],
  );

  return (
    <MockDataContext.Provider value={value}>
      {children}
    </MockDataContext.Provider>
  );
}

MockDataProvider.displayName = "MockDataProvider";

export function useMockData(): MockDataContextValue {
  const ctx = useContext(MockDataContext);
  if (!ctx) {
    throw new Error("useMockData must be used within MockDataProvider");
  }
  return ctx;
}
