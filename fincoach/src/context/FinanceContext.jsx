import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { getProfile, saveProfile } from "../services/profileService";
import { getDashboard } from "../services/dashboardService";
const Ctx = createContext(null);
export const useFinance = () => useContext(Ctx);
export function FinanceProvider({ children }) {
  const [profile, setProfile] = useState(null),
    [stats, setStats] = useState(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      setProfile(await getProfile());
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
  const save = async (data) => {
    await saveProfile(data, !!profile);
    await refresh();
  };
  return (
    <Ctx.Provider value={{ profile, stats, loading, error, save }}>
      {children}
    </Ctx.Provider>
  );
}
