import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { getProfile, saveProfile, clearData } from "../services/profileService";
import { getDashboard } from "../services/dashboardService";
const Ctx = createContext(null);
export const useFinance = () => useContext(Ctx);
export function FinanceProvider({ children }) {
  const [profile, setProfile] = useState(null),
    [stats, setStats] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [profileOpen, setProfileOpen] = useState(false),
    [afterSave, setAfterSave] = useState(null),
    [hidden, setHiddenState] = useState(() => {
      try {
        return localStorage.getItem("finbot.hide") === "1";
      } catch {
        return false;
      }
    });
  const refresh = useCallback(async () => {
    try {
      const p = await getProfile();
      setProfile(p && Object.keys(p).length ? p : null);
      setStats(await getDashboard());
      setError("");
    } catch (e) {
      setError("Could not load your data. Check the backend connection.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);
  const setHidden = (v) => {
    setHiddenState(v);
    try {
      localStorage.setItem("finbot.hide", v ? "1" : "0");
    } catch {}
  };
  const openProfile = (goTo = null) => {
    setAfterSave(goTo);
    setProfileOpen(true);
  };
  const closeProfile = () => setProfileOpen(false);
  const clear = async (everything) => {
    await clearData(everything);
    await refresh();
  };
  const save = async (data) => {
    await saveProfile(data, !!profile);
    await refresh();
  };
  return (
    <Ctx.Provider value={{
        profile, stats, loading, error, save, clear,
        profileOpen, openProfile, closeProfile, afterSave,
        hidden, setHidden,
      }}>
      {children}
    </Ctx.Provider>
  );
}
