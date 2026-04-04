import api from './client';
import type {
  Alert,
  Customer,
  DashboardSummary,
  Device,
  MonthlyPlan,
  MonthlySubscription,
  ParkingSession,
  ParkingSessionActionResponse,
  Payment,
  RevenueItem,
  RFIDCard,
  StaffUser,
  TokenResponse,
  Vehicle,
} from '../types';

export const authApi = {
  login: (payload: { username: string; password: string }) => api.post<TokenResponse>('/auth/login', payload).then((res) => res.data),
  me: () => api.get<StaffUser>('/auth/me').then((res) => res.data),
};

export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/dashboard/summary').then((res) => res.data),
};

export const customerApi = {
  list: (search = '') => api.get<Customer[]>('/customers', { params: search ? { search } : {} }).then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<Customer>('/customers', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<Customer>(`/customers/${id}`, payload).then((res) => res.data),
  remove: (id: number) => api.delete(`/customers/${id}`).then((res) => res.data),
};

export const vehicleApi = {
  list: (search = '') => api.get<Vehicle[]>('/vehicles', { params: search ? { search } : {} }).then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<Vehicle>('/vehicles', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<Vehicle>(`/vehicles/${id}`, payload).then((res) => res.data),
  remove: (id: number) => api.delete(`/vehicles/${id}`).then((res) => res.data),
};

export const cardApi = {
  list: () => api.get<RFIDCard[]>('/rfid-cards').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<RFIDCard>('/rfid-cards', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<RFIDCard>(`/rfid-cards/${id}`, payload).then((res) => res.data),
};

export const planApi = {
  list: () => api.get<MonthlyPlan[]>('/monthly-plans').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<MonthlyPlan>('/monthly-plans', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<MonthlyPlan>(`/monthly-plans/${id}`, payload).then((res) => res.data),
  remove: (id: number) => api.delete(`/monthly-plans/${id}`).then((res) => res.data),
};

export const subscriptionApi = {
  list: () => api.get<MonthlySubscription[]>('/monthly-subscriptions').then((res) => res.data),
  expiringSoon: () => api.get<MonthlySubscription[]>('/monthly-subscriptions/expiring-soon').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<MonthlySubscription>('/monthly-subscriptions', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<MonthlySubscription>(`/monthly-subscriptions/${id}`, payload).then((res) => res.data),
  remove: (id: number) => api.delete(`/monthly-subscriptions/${id}`).then((res) => res.data),
};

export const sessionApi = {
  list: () => api.get<ParkingSession[]>('/parking-sessions').then((res) => res.data),
  current: () => api.get<ParkingSession[]>('/parking-sessions/current').then((res) => res.data),
  searchByPlate: (plate_number: string) => api.get<ParkingSession[]>('/parking-sessions/search-by-plate', { params: { plate_number } }).then((res) => res.data),
  checkIn: (payload: { card_uid: string; plate_number: string; gate_id: number; image_url?: string }) => api.post<ParkingSessionActionResponse>('/parking-sessions/check-in', payload).then((res) => res.data),
  checkOut: (payload: { card_uid: string; plate_number: string; gate_id: number; image_url?: string; payment_method: string }) => api.post<ParkingSessionActionResponse>('/parking-sessions/check-out', payload).then((res) => res.data),
};

export const paymentApi = {
  list: () => api.get<Payment[]>('/payments').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<Payment>('/payments', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<Payment>(`/payments/${id}`, payload).then((res) => res.data),
  revenueDaily: () => api.get<RevenueItem[]>('/payments/revenue/daily').then((res) => res.data),
  revenueMonthly: () => api.get<RevenueItem[]>('/payments/revenue/monthly').then((res) => res.data),
};

export const deviceApi = {
  list: () => api.get<Device[]>('/devices').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<Device>('/devices', payload).then((res) => res.data),
  update: (id: number, payload: Record<string, unknown>) => api.put<Device>(`/devices/${id}`, payload).then((res) => res.data),
  updateStatus: (id: number, status: string) => api.put<Device>(`/devices/${id}/status`, { status }).then((res) => res.data),
  remove: (id: number) => api.delete(`/devices/${id}`).then((res) => res.data),
  gasAlert: (payload: { device_id: number; gas_value: number }) => api.post('/devices/gas-alert', payload).then((res) => res.data),
};

export const alertApi = {
  list: () => api.get<Alert[]>('/alerts').then((res) => res.data),
  unresolvedGas: () => api.get<Alert[]>('/alerts/gas/unresolved').then((res) => res.data),
  create: (payload: Record<string, unknown>) => api.post<Alert>('/alerts', payload).then((res) => res.data),
  acknowledge: (id: number) => api.put<Alert>(`/alerts/${id}/acknowledge`).then((res) => res.data),
  resolve: (id: number) => api.put<Alert>(`/alerts/${id}/resolve`).then((res) => res.data),
};
