import { useLocalStorage } from "@mantine/hooks";
import { createContext, type ReactNode, useContext, useMemo } from "react";

interface DeveloperModeContextValue {
  enabled: boolean;
  toggle: () => void;
  setEnabled: (enabled: boolean) => void;
}

const DeveloperModeContext = createContext<DeveloperModeContextValue | null>(null);

export function DeveloperModeProvider({ children }: { children: ReactNode }) {
  const [enabled, setEnabled] = useLocalStorage({
    key: "pme:developer-mode",
    defaultValue: false,
  });
  const value = useMemo(
    () => ({
      enabled,
      setEnabled,
      toggle: () => setEnabled((current) => !current),
    }),
    [enabled],
  );

  return (
    <DeveloperModeContext.Provider value={value}>{children}</DeveloperModeContext.Provider>
  );
}

export function useDeveloperMode() {
  const context = useContext(DeveloperModeContext);
  if (!context) {
    throw new Error("useDeveloperMode must be used within DeveloperModeProvider");
  }
  return context;
}
