export type ID = number;

export type StaffRole = 'admin' | 'staff';
export type UserStatus = 'active' | 'inactive';
export type CustomerType = 'walk_in' | 'monthly';
export type VehicleType = 'motorbike' | 'car' | 'bicycle' | 'truck' | 'other';
export type CardType = 'guest' | 'monthly' | 'staff';
export type CardStatus = 'available' | 'assigned' | 'lost' | 'blocked' | 'inactive';
export type SubscriptionStatus = 'active' | 'expired' | 'cancelled';
export type PaymentStatus = 'unpaid' | 'paid' | 'covered';
export type SessionStatus = 'in_progress' | 'completed' | 'lost_card' | 'abnormal';
export type PaymentMethod = 'cash' | 'bank_transfer' | 'e_wallet';
export type PaymentRecordStatus = 'pending' | 'paid' | 'failed' | 'refunded';
export type DeviceType = 'rfid_reader' | 'camera' | 'barrier' | 'gas_sensor' | 'esp32_controller' | 'display' | 'other';
export type DeviceStatus = 'online' | 'offline' | 'maintenance' | 'error';
export type AlertType = 'gas' | 'device_offline' | 'plate_mismatch' | 'barrier_error' | 'unauthorized_access' | 'other';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'open' | 'acknowledged' | 'resolved';

export interface LoginRequest { username: string; password: string; }
export interface TokenResponse { access_token: string; token_type: string; }
export interface StaffUser { user_id: ID; lot_id: ID | null; full_name: string; username: string; role: StaffRole; phone: string | null; email: string | null; status: UserStatus; created_at: string; updated_at: string; }
export interface Customer { customer_id: ID; customer_code: string; full_name: string; phone: string | null; email: string | null; address: string | null; customer_type: CustomerType; status: UserStatus; created_at: string; updated_at: string; }
export interface Vehicle { vehicle_id: ID; customer_id: ID | null; plate_number: string; vehicle_type: VehicleType; brand: string | null; model: string | null; color: string | null; status: string; created_at: string; updated_at: string; }
export interface RFIDCard { card_id: ID; card_uid: string; card_code: string | null; card_type: CardType; assigned_customer_id: ID | null; assigned_vehicle_id: ID | null; issued_at: string | null; expired_at: string | null; status: CardStatus; note: string | null; created_at: string; updated_at: string; }
export interface MonthlyPlan { plan_id: ID; plan_name: string; vehicle_type: VehicleType; duration_months: number; price: string; description: string | null; status: string; created_at: string; updated_at: string; }
export interface MonthlySubscription { subscription_id: ID; plan_id: ID; customer_id: ID; vehicle_id: ID; card_id: ID | null; start_date: string; end_date: string; registered_price: string; status: SubscriptionStatus; created_by: ID | null; created_at: string; updated_at: string; }
export interface ParkingSession { session_id: ID; session_code: string; customer_id: ID | null; vehicle_id: ID | null; card_id: ID | null; subscription_id: ID | null; vehicle_type: VehicleType; entry_gate_id: ID; exit_gate_id: ID | null; entry_time: string; exit_time: string | null; entry_plate_number: string | null; exit_plate_number: string | null; entry_plate_image: string | null; exit_plate_image: string | null; plate_match_flag: boolean; entry_staff_id: ID | null; exit_staff_id: ID | null; parking_fee: string; payment_status: PaymentStatus; session_status: SessionStatus; note: string | null; created_at: string; updated_at: string; }
export interface Payment { payment_id: ID; payment_code: string; payment_type: string; session_id: ID | null; subscription_id: ID | null; customer_id: ID | null; amount: string; payment_method: PaymentMethod; status: PaymentRecordStatus; paid_at: string | null; created_by: ID | null; note: string | null; created_at: string; updated_at: string; }
export interface Device { device_id: ID; lot_id: ID | null; zone_id: ID | null; gate_id: ID | null; device_code: string; device_name: string; device_type: DeviceType; serial_number: string | null; ip_address: string | null; firmware_version: string | null; status: DeviceStatus; installed_at: string | null; last_seen_at: string | null; note: string | null; created_at: string; updated_at: string; }
export interface Alert { alert_id: ID; device_id: ID | null; alert_type: AlertType; severity: AlertSeverity; title: string; description: string | null; status: AlertStatus; detected_at: string; acknowledged_at: string | null; resolved_at: string | null; resolved_by: ID | null; created_at: string; updated_at: string; }
export interface DashboardSummary { total_current_vehicles: number; total_unresolved_alerts: number; today_revenue: string; active_monthly_customers: number; }
export interface RevenueItem { period: string; total_amount: string; }
export interface ParkingSessionActionResponse { allow_open_barrier: boolean; message: string; session: ParkingSession; payment: Record<string, unknown> | null; }
export interface ApiErrorResponse { message?: string; errors?: unknown; }
