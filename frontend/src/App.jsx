import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Play from './pages/Play.jsx'
import AppLayout from "./layouts/AppLayout.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Goals from "./pages/Goals.jsx";
import Simulator from "./pages/Simulator.jsx";
import Expenses from "./pages/Expenses.jsx";
import News from "./pages/News.jsx";
export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/goals" element={<Goals />} />
        <Route path="/simulator" element={<Simulator />} />
        <Route path="/expenses" element={<Expenses />} />
        <Route path="/news" element={<News />} /><Route path="/play" element={<Play />} />
      </Route>
    </Routes>
  );
}
