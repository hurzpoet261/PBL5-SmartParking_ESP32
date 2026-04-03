import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const menu = [
  ['/', 'Dashboard'],
  ['/customers', 'Customers'],
  ['/vehicles', 'Vehicles'],
  ['/rfid-cards', 'RFID Cards'],
  ['/plans', 'Monthly Plans'],
  ['/subscriptions', 'Subscriptions'],
  ['/sessions', 'Parking Sessions'],
  ['/payments', 'Payments'],
  ['/devices', 'Devices'],
  ['/alerts', 'Alerts'],
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link to="/" className="brand">SmartParking</Link>
        <nav>
          {menu.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            <strong>{user?.full_name}</strong>
            <span> · {user?.role}</span>
          </div>
          <button className="button secondary" onClick={logout}>Logout</button>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
