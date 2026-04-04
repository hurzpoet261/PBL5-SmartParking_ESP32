import { createBrowserRouter } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute';
import AppLayout from '../layouts/AppLayout';
import AlertsPage from '../pages/AlertsPage';
import CustomersPage from '../pages/CustomersPage';
import DashboardPage from '../pages/DashboardPage';
import DevicesPage from '../pages/DevicesPage';
import LoginPage from '../pages/LoginPage';
import PaymentsPage from '../pages/PaymentsPage';
import PlansPage from '../pages/PlansPage';
import RfidCardsPage from '../pages/RfidCardsPage';
import SessionsPage from '../pages/SessionsPage';
import SubscriptionsPage from '../pages/SubscriptionsPage';
import VehiclesPage from '../pages/VehiclesPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'customers', element: <CustomersPage /> },
          { path: 'vehicles', element: <VehiclesPage /> },
          { path: 'rfid-cards', element: <RfidCardsPage /> },
          { path: 'plans', element: <PlansPage /> },
          { path: 'subscriptions', element: <SubscriptionsPage /> },
          { path: 'sessions', element: <SessionsPage /> },
          { path: 'payments', element: <PaymentsPage /> },
          { path: 'devices', element: <DevicesPage /> },
          { path: 'alerts', element: <AlertsPage /> },
        ],
      },
    ],
  },
]);
