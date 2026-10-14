import { useEffect, useSyncExternalStore } from "react";
import { applyTheme, followSystem, getPreference, setPreference, subscribe, type ThemePreference } from "../theme";

const SERVER_PREFERENCE: ThemePreference = "system";

/** A preferência de tema e como trocá-la (S37-05); o mesmo valor em todas as telas que a mostram. */
export function useTheme(): [ThemePreference, (preference: ThemePreference) => void] {
  const preference = useSyncExternalStore(subscribe, getPreference, () => SERVER_PREFERENCE);
  return [preference, setPreference];
}

/** Uma vez por página: aplica a preferência e, com "do sistema", acompanha o sistema operacional. */
export function useThemeEffect() {
  useEffect(() => {
    applyTheme();
    return followSystem();
  }, []);
}
