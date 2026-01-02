import { Outlet, NavLink } from "react-router-dom";

const linkBase =
  "px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-100 transition";
const linkActive = "bg-gray-100";

export default function Layout() {
  return (
    <div className="min-h-screen bg-white text-gray-900">
      <header className="sticky top-0 z-10 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
          <div className="font-semibold">Minimalist</div>
          <nav className="flex items-center gap-1">
            <NavLink
              to="/"
              className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
              end
            >
              Home
            </NavLink>
            
            <NavLink
              to="/menu"
              className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
            >
              Menu
            </NavLink>
            <NavLink
              to="/contact"
              className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
            >
              Contact
            </NavLink>
            {/* __NAV__ */}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10">
        <Outlet />
      </main>

      <footer className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-gray-500">
          Built with CodeLaunchAI
        </div>
      </footer>
    </div>
  );
}
