import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Wallet, TrendUp, TrendDown, ArrowsLeftRight, DownloadSimple, CalendarBlank } from '@phosphor-icons/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const COLORS = ['#5C745A', '#C06B52', '#7CA1A6', '#D4A373', '#8B6E5A', '#6B8E6B', '#A67C5A', '#5A8B8E', '#C07A84', '#7A6BC0'];

const CustomPieLabel = ({ cx, cy, midAngle, outerRadius, percent, name }) => {
  if (percent < 0.04) return null;
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 24;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  const short = name && name.length > 12 ? name.slice(0, 11) + '…' : (name || '');
  return (
    <text x={x} y={y} fill="var(--app-text-secondary)" textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central" style={{ fontSize: '11px' }}>
      {short} {(percent * 100).toFixed(0)}%
    </text>
  );
};

const Dashboard = () => {
  const [accounts, setAccounts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => { loadData(); }, []);

  const loadData = async (start = '', end = '') => {
    setLoading(true);
    try {
      let url = `${API}/analytics/summary`;
      if (start && end) url += `?start_date=${start}&end_date=${end}`;
      const [accountsRes, analyticsRes] = await Promise.all([
        axios.get(`${API}/accounts`),
        axios.get(url)
      ]);
      setAccounts(accountsRes.data);
      setAnalytics(analyticsRes.data);
    } catch {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodChange = (value) => {
    setPeriod(value);
    const today = new Date();
    let start, end;
    switch (value) {
      case 'this_month':
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'last_month':
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        end = new Date(today.getFullYear(), today.getMonth(), 0);
        break;
      case 'this_fy':
        const fyStart = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
        start = new Date(fyStart, 3, 1);
        end = new Date(fyStart + 1, 2, 31);
        break;
      case 'last_fy':
        const lastFyStart = today.getMonth() >= 3 ? today.getFullYear() - 1 : today.getFullYear() - 2;
        start = new Date(lastFyStart, 3, 1);
        end = new Date(lastFyStart + 1, 2, 31);
        break;
      case 'custom':
        return;
      default:
        loadData();
        return;
    }
    const s = start.toISOString().split('T')[0];
    const e = end.toISOString().split('T')[0];
    setStartDate(s);
    setEndDate(e);
    loadData(s, e);
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

  const totalBalance = useMemo(() => accounts.reduce((s, a) => s + a.current_balance, 0), [accounts]);
  const expenseData = useMemo(() => (analytics?.category_breakdown?.filter(c => c.type === 'expense') || []).map((c, i) => ({ ...c, fill: c.color || COLORS[i % COLORS.length] })), [analytics]);
  const topExpenses = useMemo(() => [...expenseData].sort((a, b) => b.amount - a.amount).slice(0, 7), [expenseData]);
  const savingsRate = analytics?.total_income > 0 ? ((analytics.net_savings / analytics.total_income) * 100).toFixed(1) : 0;

  if (loading) return <div className="text-center py-12" style={{ color: 'var(--app-text-secondary)' }}>Loading...</div>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ color: 'var(--app-text)' }}>Dashboard</h2>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Your financial overview & analytics</p>
        </div>
        <Button onClick={handleExportBackup} data-testid="export-backup-btn"
          style={{ background: 'var(--app-card-bg)', color: 'var(--app-text)', borderColor: 'var(--app-card-border)' }}
          className="border rounded-lg">
          <DownloadSimple size={18} className="mr-2" /> Export
        </Button>
      </div>

      {/* Period Selector */}
      <div className="themed-card rounded-lg p-4 shadow-sm">
        <div className="flex items-center gap-3 flex-wrap">
          <CalendarBlank size={18} style={{ color: 'var(--app-accent)' }} />
          <div className="w-44">
            <Select value={period} onValueChange={handlePeriodChange}>
              <SelectTrigger data-testid="period-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="this_month">This Month</SelectItem>
                <SelectItem value="last_month">Last Month</SelectItem>
                <SelectItem value="this_fy">This FY (Apr–Mar)</SelectItem>
                <SelectItem value="last_fy">Last FY</SelectItem>
                <SelectItem value="custom">Custom Range</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {period === 'custom' && (
            <>
              <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}
                data-testid="start-date-input"
                className="p-2 border rounded-lg text-sm"
                style={{ borderColor: 'var(--app-card-border)', color: 'var(--app-text)', background: 'var(--app-card-bg)' }} />
              <span style={{ color: 'var(--app-text-muted)' }}>to</span>
              <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}
                data-testid="end-date-input"
                className="p-2 border rounded-lg text-sm"
                style={{ borderColor: 'var(--app-card-border)', color: 'var(--app-text)', background: 'var(--app-card-bg)' }} />
              <Button onClick={() => startDate && endDate ? loadData(startDate, endDate) : toast.error('Select both dates')}
                data-testid="apply-date-range-btn" className="themed-btn-primary rounded-lg text-sm h-9">
                Apply
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {[
          { label: 'Balance', value: `₹${totalBalance.toFixed(0)}`, icon: Wallet, color: 'var(--app-accent)', id: 'total-balance-card' },
          { label: 'Income', value: `₹${(analytics?.total_income || 0).toFixed(0)}`, icon: TrendUp, color: 'var(--app-accent)', id: 'total-income-card' },
          { label: 'Expenses', value: `₹${(analytics?.total_expense || 0).toFixed(0)}`, icon: TrendDown, color: 'var(--app-danger)', id: 'total-expense-card' },
          { label: 'Net Savings', value: `₹${(analytics?.net_savings || 0).toFixed(0)}`, icon: ArrowsLeftRight, color: analytics?.net_savings >= 0 ? 'var(--app-accent)' : 'var(--app-danger)', id: 'net-savings-card' },
          { label: 'Savings Rate', value: `${savingsRate}%`, icon: TrendUp, color: '#7CA1A6', id: 'savings-rate-card' },
        ].map(card => (
          <div key={card.id} data-testid={card.id} className="rounded-lg p-5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200"
            style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-[0.15em] font-medium" style={{ color: 'var(--app-text-secondary)' }}>{card.label}</span>
              <card.icon size={16} style={{ color: card.color }} />
            </div>
            <div className="font-heading text-xl lg:text-2xl" style={{ color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Expenses Bar */}
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Expenses</h3>
          {topExpenses.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topExpenses} layout="vertical" margin={{ left: 10, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" horizontal={false} />
                <XAxis type="number" style={{ fontSize: '11px' }} tick={{ fill: 'var(--app-text-muted)' }}
                  tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <YAxis dataKey="category" type="category" width={90} style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--app-text-secondary)' }} tickFormatter={v => v.length > 12 ? v.slice(0,11)+'…' : v} />
                <Tooltip formatter={(v) => [`₹${v.toFixed(2)}`, 'Amount']}
                  contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
                  {topExpenses.map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-center py-12 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense data yet</p>}
        </div>

        {/* Expense Breakdown Pie */}
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Expense Breakdown</h3>
          {expenseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={expenseData} cx="50%" cy="50%" outerRadius={75} innerRadius={40}
                  dataKey="amount" nameKey="category" labelLine={false} label={CustomPieLabel}>
                  {expenseData.map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => [`₹${v.toFixed(2)}`, 'Amount']}
                  contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-center py-12 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense data yet</p>}
        </div>
      </div>

      {/* Monthly Trend */}
      {analytics?.monthly_trend?.length > 0 && (
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Monthly Trend</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={analytics.monthly_trend} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
              <XAxis dataKey="month" style={{ fontSize: '11px' }} tick={{ fill: 'var(--app-text-muted)' }} />
              <YAxis style={{ fontSize: '11px' }} tick={{ fill: 'var(--app-text-muted)' }}
                tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
              <Tooltip contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }}
                formatter={(v) => [`₹${v.toFixed(2)}`]} />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="income" fill="var(--app-accent)" name="Income" radius={[4, 4, 0, 0]} />
              <Bar dataKey="expense" fill="var(--app-danger)" name="Expense" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Accounts */}
      {accounts.length > 0 && (
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Accounts</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {accounts.map(a => (
              <div key={a.id} data-testid={`account-${a.name}`} className="p-3 rounded-lg"
                style={{ border: '1px solid var(--app-card-border)' }}>
                <div className="text-[10px] uppercase tracking-[0.15em] mb-0.5" style={{ color: 'var(--app-text-secondary)' }}>{a.account_type.replace('_', ' ')}</div>
                <div className="text-sm font-medium mb-0.5" style={{ color: 'var(--app-text)' }}>{a.name}</div>
                <div className="text-lg font-heading" style={{ color: 'var(--app-accent)' }}>₹{a.current_balance.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
