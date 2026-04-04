import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute() {
  const { token, loading } = useAuth();

  if (loading) return <div className="page"><p>Loading...</p></div>;
  if (!token) return <Navigate to="/login" replace />;
  return <Outlet />;
}
