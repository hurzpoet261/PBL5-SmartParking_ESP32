import { useEffect, useState } from 'react';
import { alertApi, dashboardApi, paymentApi, sessionApi, subscriptionApi } from '../api/services';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import type { Alert, DashboardSummary, ParkingSession, RevenueItem, MonthlySubscription } from '../types';
import { formatDateTime, formatMoney } from '../utils/format';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [currentSessions, setCurrentSessions] = useState<ParkingSession[]>([]);
  const [revenue, setRevenue] = useState<RevenueItem[]>([]);
  const [expiring, setExpiring] = useState<MonthlySubscription[]>([]);

  useEffect(() => {
    Promise.all([
      dashboardApi.summary(),
      alertApi.unresolvedGas(),
      sessionApi.current(),
      paymentApi.revenueDaily(),
      subscriptionApi.expiringSoon(),
    ]).then(([summaryData, alertData, sessionData, revenueData, expiringData]) => {
      setSummary(summaryData);
      setAlerts(alertData);
      setCurrentSessions(sessionData);
      setRevenue(revenueData.slice(0, 5));
      setExpiring(expiringData);
    }).catch(console.error);
  }, []);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Quick overview of vehicles, alerts, revenue, and subscriptions." />
      <div className="stats-grid">
        <div className="stat card"><span>Vehicles inside</span><strong>{summary?.total_current_vehicles ?? '-'}</strong></div>
        <div className="stat card"><span>Open alerts</span><strong>{summary?.total_unresolved_alerts ?? '-'}</strong></div>
        <div className="stat card"><span>Today revenue</span><strong>{summary ? formatMoney(summary.today_revenue) : '-'}</strong></div>
        <div className="stat card"><span>Active monthly customers</span><strong>{summary?.active_monthly_customers ?? '-'}</strong></div>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>Current sessions</h3>
          <table><thead><tr><th>Code</th><th>Plate</th><th>Type</th><th>Entry time</th></tr></thead><tbody>
            {currentSessions.map((item) => <tr key={item.session_id}><td>{item.session_code}</td><td>{item.entry_plate_number}</td><td>{item.vehicle_type}</td><td>{formatDateTime(item.entry_time)}</td></tr>)}
          </tbody></table>
        </section>
        <section className="card">
          <h3>Open gas alerts</h3>
          <table><thead><tr><th>Title</th><th>Severity</th><th>Detected</th></tr></thead><tbody>
            {alerts.map((item) => <tr key={item.alert_id}><td>{item.title}</td><td><StatusBadge value={item.severity} /></td><td>{formatDateTime(item.detected_at)}</td></tr>)}
          </tbody></table>
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>Recent daily revenue</h3>
          <table><thead><tr><th>Period</th><th>Total</th></tr></thead><tbody>
            {revenue.map((item) => <tr key={item.period}><td>{item.period}</td><td>{formatMoney(item.total_amount)}</td></tr>)}
          </tbody></table>
        </section>
        <section className="card">
          <h3>Subscriptions expiring soon</h3>
          <table><thead><tr><th>ID</th><th>Customer ID</th><th>End date</th><th>Status</th></tr></thead><tbody>
            {expiring.map((item) => <tr key={item.subscription_id}><td>{item.subscription_id}</td><td>{item.customer_id}</td><td>{item.end_date}</td><td><StatusBadge value={item.status} /></td></tr>)}
          </tbody></table>
        </section>
      </div>
    </div>
  );
}
