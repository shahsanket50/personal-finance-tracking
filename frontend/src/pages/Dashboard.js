import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { Wallet, TrendUp, TrendDown, ArrowsLeftRight, DownloadSimple, CalendarBlank } from '@phosphor-icons/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const COLORS = ['#5C745A', '#C06B52', '#7CA1A6', '#D4A373', '#8B6E5A', '#6B8E6B', '#A67C5A', '#5A8B8E', '#C07A84', '#7A6BC0'];

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

  // Decide: use daily trend for single-month views, monthly trend otherwise
  const isSingleMonth = ['this_month', 'last_month'].includes(period);
  const trendData = useMemo(() => {
    if (isSingleMonth && analytics?.daily_trend?.length > 0) {
      return analytics.daily_trend.map(d => ({
        ...d,
        label: d.day.slice(8) // Just the day number (DD)
      }));
    }
    return (analytics?.monthly_trend || []).map(m => ({ ...m, label: m.month }));
  }, [analytics, isSingleMonth]);

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
            <div>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={expenseData} cx="50%" cy="50%" outerRadius={70} innerRadius={38}
                    dataKey="amount" nameKey="category" isAnimationActive={false}>
                    {expenseData.map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v, name) => [`₹${v.toFixed(2)}`, name]}
                    contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1.5 max-h-[100px] overflow-y-auto">
                {[...expenseData].sort((a, b) => b.amount - a.amount).map((e, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: e.fill || COLORS[i % COLORS.length] }} />
                      <span className="truncate" style={{ color: 'var(--app-text-secondary)' }}>{e.category}</span>
                    </div>
                    <span className="shrink-0 ml-2 font-medium" style={{ color: 'var(--app-text)' }}>
                      ₹{e.amount >= 1000 ? `${(e.amount/1000).toFixed(1)}k` : e.amount.toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : <p className="text-center py-12 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense data yet</p>}
        </div>
      </div>

      {/* Trend Chart — daily for month views, monthly for broader periods */}
      {trendData.length > 0 && (
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>
            {isSingleMonth ? 'Daily Trend' : 'Monthly Trend'}
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={trendData} barGap={2}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
              <XAxis dataKey="label" style={{ fontSize: '11px' }} tick={{ fill: 'var(--app-text-muted)' }} />
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

      {/* Top Creditors & Debitors Row */}
      {((analytics?.top_creditors?.length > 0) || (analytics?.top_debitors?.length > 0)) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Debitors (where money goes) */}
          {analytics?.top_debitors?.length > 0 && (
            <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
              <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Spends</h3>
              <div className="space-y-2">
                {analytics.top_debitors.slice(0, 8).map((d, i) => (
                  <div key={i} data-testid={`top-debitor-${i}`} className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-xs font-medium w-5 text-center" style={{ color: 'var(--app-text-muted)' }}>{i + 1}</span>
                      <span className="text-sm truncate" style={{ color: 'var(--app-text)' }}>{d.description}</span>
                    </div>
                    <span className="text-sm font-medium shrink-0 ml-2" style={{ color: '#C06B52' }}>
                      ₹{d.amount >= 1000 ? `${(d.amount/1000).toFixed(1)}k` : d.amount.toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Creditors (where money comes from) */}
          {analytics?.top_creditors?.length > 0 && (
            <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
              <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Income Sources</h3>
              <div className="space-y-2">
                {analytics.top_creditors.slice(0, 8).map((c, i) => (
                  <div key={i} data-testid={`top-creditor-${i}`} className="flex items-center justify-between py-1.5">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-xs font-medium w-5 text-center" style={{ color: 'var(--app-text-muted)' }}>{i + 1}</span>
                      <span className="text-sm truncate" style={{ color: 'var(--app-text)' }}>{c.description}</span>
                    </div>
                    <span className="text-sm font-medium shrink-0 ml-2" style={{ color: '#5C745A' }}>
                      ₹{c.amount >= 1000 ? `${(c.amount/1000).toFixed(1)}k` : c.amount.toFixed(0)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Accounts with period credits/debits */}
      {analytics?.account_summary?.length > 0 && (
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Accounts</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {analytics.account_summary.map((a, i) => (
              <div key={i} data-testid={`account-summary-${a.name}`} className="p-4 rounded-lg"
                style={{ border: '1px solid var(--app-card-border)' }}>
                <div className="text-[10px] uppercase tracking-[0.15em] mb-0.5" style={{ color: 'var(--app-text-secondary)' }}>{a.type.replace('_', ' ')}</div>
                <div className="text-sm font-medium mb-2" style={{ color: 'var(--app-text)' }}>{a.name}</div>
                <div className="flex justify-between text-xs">
                  <div>
                    <div style={{ color: 'var(--app-text-muted)' }}>Credits</div>
                    <div className="font-medium" style={{ color: '#5C745A' }}>₹{a.credits.toFixed(0)}</div>
                  </div>
                  <div className="text-right">
                    <div style={{ color: 'var(--app-text-muted)' }}>Debits</div>
                    <div className="font-medium" style={{ color: '#C06B52' }}>₹{a.debits.toFixed(0)}</div>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t text-xs text-right" style={{ borderColor: 'var(--app-card-border)' }}>
                  <span style={{ color: 'var(--app-text-muted)' }}>Balance: </span>
                  <span className="font-heading text-sm" style={{ color: 'var(--app-accent)' }}>₹{a.balance.toFixed(0)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
