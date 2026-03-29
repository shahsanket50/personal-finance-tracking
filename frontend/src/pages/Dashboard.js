import { useState, useEffect } from 'react';
import axios from 'axios';
import { Wallet, TrendUp, TrendDown, ArrowsLeftRight, DownloadSimple } from '@phosphor-icons/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Dashboard = () => {
  const [accounts, setAccounts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [accountsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/accounts`),
        axios.get(`${API}/analytics/summary`)
      ]);
      setAccounts(accountsRes.data);
      setAnalytics(analyticsRes.data);
    } catch (err) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleExportBackup = async () => {
    try {
      const res = await axios.get(`${API}/backup/export`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `moneyinsights-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Backup downloaded');
    } catch { toast.error('Export failed'); }
  };

  if (loading) return <div className="text-center py-12" style={{ color: 'var(--app-text-secondary)' }}>Loading...</div>;

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.current_balance, 0);
  const expenseData = analytics?.category_breakdown?.filter(c => c.type === 'expense') || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ color: 'var(--app-text)' }}>Dashboard</h2>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Overview of your financial health</p>
        </div>
        <Button onClick={handleExportBackup} data-testid="export-backup-btn"
          style={{ background: 'var(--app-card-bg)', color: 'var(--app-text)', borderColor: 'var(--app-card-border)' }}
          className="border rounded-lg">
          <DownloadSimple size={18} className="mr-2" /> Export Backup
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Balance', value: `₹${totalBalance.toFixed(2)}`, icon: Wallet, color: 'var(--app-accent)', id: 'total-balance-card' },
          { label: 'Income', value: `₹${analytics?.total_income?.toFixed(2) || 0}`, icon: TrendUp, color: 'var(--app-accent)', id: 'total-income-card' },
          { label: 'Expenses', value: `₹${analytics?.total_expense?.toFixed(2) || 0}`, icon: TrendDown, color: 'var(--app-danger)', id: 'total-expense-card' },
          { label: 'Net Savings', value: `₹${analytics?.net_savings?.toFixed(2) || 0}`, icon: ArrowsLeftRight, color: analytics?.net_savings >= 0 ? 'var(--app-accent)' : 'var(--app-danger)', id: 'net-savings-card' },
        ].map(card => (
          <div key={card.id} data-testid={card.id} className="rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
            style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs uppercase tracking-[0.2em]" style={{ color: 'var(--app-text-secondary)' }}>{card.label}</span>
              <card.icon size={20} style={{ color: card.color }} />
            </div>
            <div className="font-heading text-3xl" style={{ color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg p-6 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Expense Breakdown</h3>
          {expenseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart><Pie data={expenseData} cx="50%" cy="50%" labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80} dataKey="amount">
                {expenseData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie><Tooltip /></PieChart>
            </ResponsiveContainer>
          ) : <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No expense data</p>}
        </div>
        <div className="rounded-lg p-6 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Monthly Trend</h3>
          {analytics?.monthly_trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
                <XAxis dataKey="month" style={{ fontSize: '12px' }} />
                <YAxis style={{ fontSize: '12px' }} />
                <Tooltip /><Legend />
                <Bar dataKey="income" fill="var(--app-accent)" name="Income" />
                <Bar dataKey="expense" fill="var(--app-danger)" name="Expense" />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No monthly data</p>}
        </div>
      </div>

      <div className="rounded-lg p-6 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
        <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Accounts</h3>
        {accounts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {accounts.map(account => (
              <div key={account.id} data-testid={`account-${account.name}`} className="p-4 rounded-lg"
                style={{ border: '1px solid var(--app-card-border)' }}>
                <div className="text-xs uppercase tracking-[0.2em] mb-1" style={{ color: 'var(--app-text-secondary)' }}>{account.account_type.replace('_', ' ')}</div>
                <div className="font-medium mb-1" style={{ color: 'var(--app-text)' }}>{account.name}</div>
                <div className="text-lg font-heading" style={{ color: 'var(--app-accent)' }}>₹{account.current_balance.toFixed(2)}</div>
              </div>
            ))}
          </div>
        ) : <p className="text-center py-6" style={{ color: 'var(--app-text-muted)' }}>No accounts yet</p>}
      </div>
    </div>
  );
};

export default Dashboard;
