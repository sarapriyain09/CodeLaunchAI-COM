import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import NotFound from "./pages/NotFound";

// Pages inserted by generator:
import Home from "./pages/Home";
import Menu from "./pages/Menu";
import Contact from "./pages/Contact";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        
        <Route path="/menu" element={<Menu />} />
        <Route path="/contact" element={<Contact />} />
        {/* __ROUTES__ */}
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
