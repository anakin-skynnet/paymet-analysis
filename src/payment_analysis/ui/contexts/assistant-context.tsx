import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface AssistantContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  openAssistant: () => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const openAssistant = useCallback(() => setOpen(true), []);
  const value = useMemo(
    () => ({ open, setOpen, openAssistant }),
    [open, openAssistant]
  );
  return (
    <AssistantContext.Provider value={value}>
      {children}
    </AssistantContext.Provider>
  );
}

export function useAssistant() {
  const ctx = useContext(AssistantContext);
  if (!ctx) {
    throw new Error("useAssistant must be used within AssistantProvider");
  }
  return ctx;
}

/** Safe hook: returns null if outside provider (e.g. on non-sidebar routes). */
export function useAssistantOptional() {
  return useContext(AssistantContext);
}
