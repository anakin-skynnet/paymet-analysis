import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEFAULT_ENTITY_CODE } from "@/config/countries";

const STORAGE_KEY = "payment-analysis-entity";

function loadStoredEntity(): string {
  if (typeof window === "undefined") return DEFAULT_ENTITY_CODE;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const code = stored?.trim();
    if (code) return code;
  } catch {
    // ignore
  }
  return DEFAULT_ENTITY_CODE;
}

function saveEntity(code: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    // ignore
  }
}

interface EntityContextValue {
  entity: string;
  setEntity: (code: string) => void;
}

const EntityContext = createContext<EntityContextValue | null>(null);

export function EntityProvider({ children }: { children: ReactNode }) {
  const [entity, setEntityState] = useState(loadStoredEntity);

  const setEntity = useCallback((code: string) => {
    setEntityState(code);
    saveEntity(code);
  }, []);

  const value = useMemo(
    () => ({ entity, setEntity }),
    [entity, setEntity],
  );

  return (
    <EntityContext.Provider value={value}>
      {children}
    </EntityContext.Provider>
  );
}

EntityProvider.displayName = "EntityProvider";

export function useEntity(): EntityContextValue {
  const ctx = useContext(EntityContext);
  if (!ctx) {
    throw new Error("useEntity must be used within EntityProvider");
  }
  return ctx;
}

export function useEntityOptional(): EntityContextValue | null {
  return useContext(EntityContext);
}
