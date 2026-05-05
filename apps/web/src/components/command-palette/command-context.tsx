"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export interface CommandAction {
  id: string;
  label: string;
  icon?: ReactNode;
  shortcut?: string;
  onSelect: () => void;
  group?: string;
}

interface CommandContextValue {
  actions: CommandAction[];
  registerActions: (actions: CommandAction[]) => void;
  clearActions: () => void;
}

const CommandCtx = createContext<CommandContextValue>({
  actions: [],
  registerActions: () => {},
  clearActions: () => {},
});

export function CommandProvider({ children }: { children: ReactNode }) {
  const [actions, setActions] = useState<CommandAction[]>([]);

  const registerActions = useCallback((newActions: CommandAction[]) => {
    setActions(newActions);
  }, []);

  const clearActions = useCallback(() => {
    setActions([]);
  }, []);

  return (
    <CommandCtx.Provider value={{ actions, registerActions, clearActions }}>
      {children}
    </CommandCtx.Provider>
  );
}

export function useCommandActions() {
  return useContext(CommandCtx);
}
