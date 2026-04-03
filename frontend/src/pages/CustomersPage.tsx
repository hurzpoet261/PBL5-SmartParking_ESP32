import { FormEvent, useEffect, useState } from 'react';
import { customerApi } from '../api/services';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';
import type { Customer, CustomerType, UserStatus } from '../types';

const initialForm = { customer_code: '', full_name: '', phone: '', email: '', address: '', customer_type: 'walk_in' as CustomerType, status: 'active' as UserStatus };

export default function CustomersPage() {
  const [items, setItems] = useState<Customer[]>([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');

  const loadData = () => customerApi.list(search).then(setItems).catch((e) => setError(e.message));
  useEffect(() => { loadData(); }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setError('');
      const payload = { ...form, phone: form.phone || null, email: form.email || null, address: form.address || null };
      editingId ? await customerApi.update(editingId, payload) : await customerApi.create(payload);
      setForm(initialForm); setEditingId(null); loadData();
    } catch (err) { setError(err instanceof Error ? err.message : 'Save failed'); }
  };

  const startEdit = (item: Customer) => { setEditingId(item.customer_id); setForm({ customer_code: item.customer_code, full_name: item.full_name, phone: item.phone || '', email: item.email || '', address: item.address || '', customer_type: item.customer_type, status: item.status }); };
  const removeItem = async (id: number) => { if (!confirm('Delete this customer?')) return; try { await customerApi.remove(id); loadData(); } catch (err) { setError(err instanceof Error ? err.message : 'Delete failed'); } };

  return <div><PageHeader title="Customers" subtitle="Create, update, search, and delete parking customers." />
    {error ? <div className="alert error">{error}</div> : null}
    <div className="grid-2"><form className="card form-grid" onSubmit={handleSubmit}>
      <h3>{editingId ? 'Edit customer' : 'Add customer'}</h3>
      <label>Code<input value={form.customer_code} onChange={(e) => setForm({ ...form, customer_code: e.target.value })} required /></label>
      <label>Full name<input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required /></label>
      <label>Phone<input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
      <label>Email<input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
      <label>Address<input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></label>
      <label>Type<select value={form.customer_type} onChange={(e) => setForm({ ...form, customer_type: e.target.value as CustomerType })}><option value="walk_in">Walk in</option><option value="monthly">Monthly</option></select></label>
      <label>Status<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as UserStatus })}><option value="active">Active</option><option value="inactive">Inactive</option></select></label>
      <div className="actions"><button className="button">{editingId ? 'Update' : 'Create'}</button><button type="button" className="button secondary" onClick={() => { setForm(initialForm); setEditingId(null); }}>Clear</button></div>
    </form>
    <section className="card"><div className="toolbar"><input placeholder="Search by name or phone" value={search} onChange={(e) => setSearch(e.target.value)} /><button className="button secondary" onClick={loadData}>Search</button></div>
      <table><thead><tr><th>Code</th><th>Name</th><th>Phone</th><th>Type</th><th>Status</th><th></th></tr></thead><tbody>
      {items.map((item) => <tr key={item.customer_id}><td>{item.customer_code}</td><td>{item.full_name}</td><td>{item.phone}</td><td>{item.customer_type}</td><td><StatusBadge value={item.status} /></td><td className="actions"><button className="button small secondary" onClick={() => startEdit(item)}>Edit</button><button className="button small danger" onClick={() => removeItem(item.customer_id)}>Delete</button></td></tr>)}
      </tbody></table></section></div></div>;
}
