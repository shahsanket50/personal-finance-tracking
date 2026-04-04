import { useState, useEffect } from 'react';
import axios from 'axios';
import { Buildings, Scales, BookOpen, Receipt, ArrowsLeftRight, ChartBar } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AccountingDashboard = () => {
  const [company, setCompany] = useState(null);
  const [stats, setStats] = useState({ ledgers: 0, vouchers: 0, groups: 0 });
  const [trialBalance, setTrialBalance] = useState(null);
  const [profitLoss, setProfitLoss] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', address: '', gstin: '', pan: '', fy_start_month: 4 });
  const [migrateLoading, setMigrateLoading] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [companyRes, ledgersRes, vouchersRes, groupsRes, tbRes, plRes] = await Promise.all([
        axios.get(`${API}/company`),
        axios.get(`${API}/ledgers`),
        axios.get(`${API}/vouchers`),
        axios.get(`${API}/account-groups`),
        axios.get(`${API}/trial-balance`),
        axios.get(`${API}/profit-loss`),
      ]);
      setCompany(companyRes.data);
      setStats({
        ledgers: ledgersRes.data.length,
        vouchers: vouchersRes.data.length,
        groups: groupsRes.data.length,
      });
      setTrialBalance(tbRes.data);
      setProfitLoss(plRes.data);
      setEditForm({
        name: companyRes.data.name || '',
        address: companyRes.data.address || '',
        gstin: companyRes.data.gstin || '',
        pan: companyRes.data.pan || '',
        fy_start_month: companyRes.data.fy_start_month || 4,
      });
    } catch {
      toast.error('Failed to load accounting data');
    } finally {
      setLoading(false);
    }
  };

  const updateCompany = async () => {
    try {
      await axios.put(`${API}/company`, editForm);
      toast.success('Company updated');
      setEditOpen(false);
      loadData();
    } catch {
      toast.error('Failed to update company');
    }
  };

  const migrateTransactions = async () => {
    setMigrateLoading(true);
    try {
      const res = await axios.post(`${API}/migrate-to-accounting`);
      toast.success(res.data.message);
      loadData();
    } catch {
      toast.error('Migration failed');
    } finally {
      setMigrateLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  const summaryCards = [
    { label: 'Account Groups', value: stats.groups, icon: ChartBar, color: '#5C745A' },
    { label: 'Ledgers', value: stats.ledgers, icon: BookOpen, color: '#7CA1A6' },
    { label: 'Vouchers', value: stats.vouchers, icon: Receipt, color: '#C06B52' },
    { label: 'Trial Balance', value: trialBalance?.is_balanced ? 'Balanced' : 'Unbalanced', icon: Scales, color: trialBalance?.is_balanced ? '#5C745A' : '#C06B52' },
  ];

  return (
    <div className="space-y-6" data-testid="accounting-dashboard">
      {/* Company Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>
            {company?.name || 'My Business'}
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-muted)' }}>
            {company?.gstin ? `GSTIN: ${company.gstin}` : 'Accounting Dashboard'}
            {company?.pan ? ` | PAN: ${company.pan}` : ''}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={migrateTransactions} disabled={migrateLoading} data-testid="migrate-btn">
            <ArrowsLeftRight size={16} className="mr-1.5" />
            {migrateLoading ? 'Migrating...' : 'Sync Transactions'}
          </Button>
          <Dialog open={editOpen} onOpenChange={setEditOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" data-testid="edit-company-btn">
                <Buildings size={16} className="mr-1.5" /> Edit Company
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Company Details</DialogTitle>
              </DialogHeader>
              <div className="space-y-3 pt-2">
                <div>
                  <Label>Company Name</Label>
                  <Input value={editForm.name} onChange={e => setEditForm(p => ({ ...p, name: e.target.value }))} data-testid="company-name-input" />
                </div>
                <div>
                  <Label>Address</Label>
                  <Input value={editForm.address} onChange={e => setEditForm(p => ({ ...p, address: e.target.value }))} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>GSTIN</Label>
                    <Input value={editForm.gstin} onChange={e => setEditForm(p => ({ ...p, gstin: e.target.value }))} />
                  </div>
                  <div>
                    <Label>PAN</Label>
                    <Input value={editForm.pan} onChange={e => setEditForm(p => ({ ...p, pan: e.target.value }))} />
                  </div>
                </div>
                <Button onClick={updateCompany} className="w-full" data-testid="save-company-btn">Save</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {summaryCards.map(card => (
          <div key={card.label} className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }} data-testid={`stat-${card.label.toLowerCase().replace(/\s/g, '-')}`}>
            <div className="flex items-center gap-2 mb-2">
              <card.icon size={20} style={{ color: card.color }} />
              <span className="text-xs font-medium" style={{ color: 'var(--app-text-muted)' }}>{card.label}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: card.color }}>{card.value}</p>
          </div>
        ))}
      </div>

      {/* P&L Quick View */}
      {profitLoss && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border rounded-lg p-5" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--app-text-muted)' }}>Total Income</p>
            <p className="text-2xl font-bold" style={{ color: '#5C745A' }}>{profitLoss.total_income.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-5" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--app-text-muted)' }}>Total Expenses</p>
            <p className="text-2xl font-bold" style={{ color: '#C06B52' }}>{profitLoss.total_expenses.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-5" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <p className="text-xs font-medium mb-1" style={{ color: 'var(--app-text-muted)' }}>Net Profit</p>
            <p className="text-2xl font-bold" style={{ color: profitLoss.net_profit >= 0 ? '#5C745A' : '#C06B52' }}>
              {profitLoss.net_profit.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}
            </p>
          </div>
        </div>
      )}

      {/* Trial Balance Quick View */}
      {trialBalance && trialBalance.rows.length > 0 && (
        <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
          <div className="p-4 border-b" style={{ borderColor: 'var(--app-border)' }}>
            <h3 className="font-semibold" style={{ color: 'var(--app-text)' }}>Trial Balance Summary</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'var(--app-bg)' }}>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Ledger</th>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Group</th>
                  <th className="text-right px-4 py-2.5 font-medium" style={{ color: '#5C745A' }}>Debit</th>
                  <th className="text-right px-4 py-2.5 font-medium" style={{ color: '#C06B52' }}>Credit</th>
                </tr>
              </thead>
              <tbody>
                {trialBalance.rows.slice(0, 10).map((row, i) => (
                  <tr key={i} className="border-t" style={{ borderColor: 'var(--app-border)' }}>
                    <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>{row.ledger_name}</td>
                    <td className="px-4 py-2" style={{ color: 'var(--app-text-muted)' }}>{row.group_name}</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#5C745A' }}>{row.debit > 0 ? row.debit.toLocaleString('en-IN') : '-'}</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#C06B52' }}>{row.credit > 0 ? row.credit.toLocaleString('en-IN') : '-'}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--app-text-muted)' }}>
                  <td className="px-4 py-2.5" colSpan={2} style={{ color: 'var(--app-text)' }}>Total</td>
                  <td className="px-4 py-2.5 text-right font-mono" style={{ color: '#5C745A' }}>{trialBalance.total_debit.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-2.5 text-right font-mono" style={{ color: '#C06B52' }}>{trialBalance.total_credit.toLocaleString('en-IN')}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccountingDashboard;
