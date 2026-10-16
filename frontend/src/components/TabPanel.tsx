import type { ReactNode } from "react";
import { panelId, tabId } from "../ui";

interface TabPanelProps {
  /** No celular, cada painel é uma aba; no computador, todos ficam à vista (S37-02). */
  narrow: boolean;
  prefix: string;
  id: string;
  active: string;
  children: ReactNode;
}

/** O painel de uma aba do `TabList`, ou só o conteúdo quando não há abas. */
export function TabPanel({ narrow, prefix, id, active, children }: TabPanelProps) {
  if (!narrow) return children;
  return (
    <div
      role="tabpanel"
      id={panelId(prefix, id)}
      aria-labelledby={tabId(prefix, id)}
      hidden={active !== id}
      className="flex flex-col gap-6"
    >
      {children}
    </div>
  );
}
