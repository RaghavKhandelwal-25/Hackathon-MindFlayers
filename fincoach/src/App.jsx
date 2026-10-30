import { Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout.jsx'; import Dashboard from './pages/Dashboard.jsx'; import Goals from './pages/Goals.jsx'
export default function App() {
  return (<Routes><Route element={<AppLayout />}><Route path="/" element={<Dashboard />} /><Route path="/goals" element={<Goals />} /></Route></Routes>)
}
