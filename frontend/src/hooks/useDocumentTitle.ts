import { useEffect } from "react";

export const APP_NAME = "IP-Checker";

/** O `<title>` de cada tela (S26-01): o leitor de tela e a aba dizem onde a pessoa está. */
export function useDocumentTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · ${APP_NAME}`;
    return () => {
      document.title = APP_NAME;
    };
  }, [title]);
}
