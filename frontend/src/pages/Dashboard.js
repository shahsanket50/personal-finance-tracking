import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Wallet, TrendUp, TrendDown, ArrowsLeftRight, DownloadSimple, CalendarBlank, ChartBar, ChartLine as ChartLineIcon, ChartDonut, Waveform } from '@phosphor-icons/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, LineChart, Line, AreaChart, Area } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const COLORS = ['#5C745A', '#C06B52', '#7CA1A6', '#D4A373', '#8B6E5A', '#6B8E6B', '#A67C5A', '#5A8B8E', '#C07A84', '#7A6BC0'];

const CHART_TYPES = [
  { id: 'bar', label: 'Bar', icon: ChartBar },
  { id: 'line', label: 'Line', icon: ChartLineIcon },
  { id: 'area', label: 'Area', icon: Waveform },
];

const Dashboard = () => {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [trendChartType, setTrendChartType] = useState('bar');
  const [expenseChartType, setExpenseChartType] = useState('pie');

  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Navigate to transactions with filters
  const goToTransactions = (params = {}) => {
    const search = new URLSearchParams();
    if (params.type) search.set('type', params.type);
    if (params.category) search.set('category', params.category);
    if (params.search) search.set('search', params.search);
    if (params.dateFrom) search.set('dateFrom', params.dateFrom);
    if (params.dateTo) search.set('dateTo', params.dateTo);
    if (startDate && endDate) {
      if (!params.dateFrom) search.set('dateFrom', startDate);
      if (!params.dateTo) search.set('dateTo', endDate);
    }
    navigate(`/transactions?${search.toString()}`);
  };

  const totalBalance = useMemo(() => accounts.reduce((s, a) => s + a.current_balance, 0), [accounts]);
  const expenseData = useMemo(() => (analytics?.category_breakdown?.filter(c => c.type === 'expense') || []).map((c, i) => ({ ...c, fill: c.color || COLORS[i % COLORS.length] })), [analytics]);
  const totalExpenseSum = useMemo(() => expenseData.reduce((s, e) => s + e.amount, 0), [expenseData]);
  const topExpenses = useMemo(() => [...expenseData].sort((a, b) => b.amount - a.amount).slice(0, 7), [expenseData]);
  const savingsRate = analytics?.total_income > 0 ? ((analytics.net_savings / analytics.total_income) * 100).toFixed(1) : 0;

  const isSingleMonth = ['this_month', 'last_month'].includes(period);
  const trendData = useMemo(() => {
    if (isSingleMonth && analytics?.daily_trend?.length > 0) {
      return analytics.daily_trend.map(d => ({ ...d, label: d.day.slice(8) }));
    }
    return (analytics?.monthly_trend || []).map(m => ({ ...m, label: m.month }));
  }, [analytics, isSingleMonth]);

  // Custom pie label with percentage
  const renderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.03) return null; // Skip tiny slices
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    return (
      <text x={x} y={y} fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={10} fontWeight={600}>
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  // Month key → date range helper
  const getMonthDateRange = (monthKey) => {
    // monthKey is "YYYY-MM"
    const [y, m] = monthKey.split('-').map(Number);
    const start = `${y}-${String(m).padStart(2, '0')}-01`;
    const lastDay = new Date(y, m, 0).getDate();
    const end = `${y}-${String(m).padStart(2, '0')}-${lastDay}`;
    return { start, end };
  };

  const getDayDateRange = (dayKey) => {
    return { start: dayKey, end: dayKey };
  };

  // Render trend chart based on selected type
  const renderTrendChart = () => {
    const commonProps = { data: trendData };
    const xAxisProps = { dataKey: "label", style: { fontSize: '11px' }, tick: { fill: 'var(--app-text-muted)' } };
    const yAxisProps = { style: { fontSize: '11px' }, tick: { fill: 'var(--app-text-muted)' }, tickFormatter: v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v };
    const tooltipProps = {
      contentStyle: { background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' },
      formatter: (v) => [`₹${v.toFixed(2)}`]
    };

    const handleTrendClick = (data) => {
      if (!data?.activePayload?.[0]) return;
      const item = data.activePayload[0].payload;
      if (item.month) {
        const { start, end } = getMonthDateRange(item.month);
        goToTransactions({ dateFrom: start, dateTo: end });
      } else if (item.day) {
        goToTransactions({ dateFrom: item.day, dateTo: item.day });
      }
    };

    switch (trendChartType) {
      case 'line':
        return (
          <LineChart {...commonProps} onClick={handleTrendClick}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip {...tooltipProps} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line type="monotone" dataKey="income" stroke="var(--app-accent)" name="Income" strokeWidth={2} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="expense" stroke="var(--app-danger)" name="Expense" strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart {...commonProps} onClick={handleTrendClick}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip {...tooltipProps} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Area type="monotone" dataKey="income" fill="var(--app-accent)" stroke="var(--app-accent)" name="Income" fillOpacity={0.15} strokeWidth={2} />
            <Area type="monotone" dataKey="expense" fill="var(--app-danger)" stroke="var(--app-danger)" name="Expense" fillOpacity={0.15} strokeWidth={2} />
          </AreaChart>
        );
      default: // bar
        return (
          <BarChart {...commonProps} barGap={2} onClick={handleTrendClick}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
            <XAxis {...xAxisProps} />
            <YAxis {...yAxisProps} />
            <Tooltip {...tooltipProps} />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Bar dataKey="income" fill="var(--app-accent)" name="Income" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expense" fill="var(--app-danger)" name="Expense" radius={[4, 4, 0, 0]} />
          </BarChart>
        );
    }
  };

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
                <SelectItem value="this_fy">This FY (Apr-Mar)</SelectItem>
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

      {/* Summary Cards - Clickable */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {[
          { label: 'Balance', value: `₹${totalBalance.toFixed(0)}`, icon: Wallet, color: 'var(--app-accent)', id: 'total-balance-card', onClick: () => goToTransactions({}) },
          { label: 'Income', value: `₹${(analytics?.total_income || 0).toFixed(0)}`, icon: TrendUp, color: 'var(--app-accent)', id: 'total-income-card', onClick: () => goToTransactions({ type: 'credit' }) },
          { label: 'Expenses', value: `₹${(analytics?.total_expense || 0).toFixed(0)}`, icon: TrendDown, color: 'var(--app-danger)', id: 'total-expense-card', onClick: () => goToTransactions({ type: 'debit' }) },
          { label: 'Net Savings', value: `₹${(analytics?.net_savings || 0).toFixed(0)}`, icon: ArrowsLeftRight, color: analytics?.net_savings >= 0 ? 'var(--app-accent)' : 'var(--app-danger)', id: 'net-savings-card', onClick: () => goToTransactions({}) },
          { label: 'Savings Rate', value: `${savingsRate}%`, icon: TrendUp, color: '#7CA1A6', id: 'savings-rate-card', onClick: () => goToTransactions({}) },
        ].map(card => (
          <div key={card.id} data-testid={card.id}
            onClick={card.onClick}
            className="rounded-lg p-5 shadow-sm hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 cursor-pointer"
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
        {/* Top Expenses Bar - Clickable */}
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Expenses</h3>
          {topExpenses.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topExpenses} layout="vertical" margin={{ left: 10, right: 16 }}
                onClick={(data) => {
                  if (data?.activePayload?.[0]) {
                    const cat = data.activePayload[0].payload.category;
                    goToTransactions({ search: cat, type: 'debit' });
                  }
                }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" horizontal={false} />
                <XAxis type="number" style={{ fontSize: '11px' }} tick={{ fill: 'var(--app-text-muted)' }}
                  tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <YAxis dataKey="category" type="category" width={90} style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--app-text-secondary)' }} tickFormatter={v => v.length > 12 ? v.slice(0,11)+'...' : v} />
                <Tooltip formatter={(v) => [`₹${v.toFixed(2)}`, 'Amount']}
                  contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="amount" radius={[0, 4, 4, 0]} className="cursor-pointer">
                  {topExpenses.map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-center py-12 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense data yet</p>}
        </div>

        {/* Expense Breakdown Pie - with percentages & clickable */}
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading text-base" style={{ color: 'var(--app-text)' }}>Expense Breakdown</h3>
            <div className="flex gap-1">
              {[
                { id: 'pie', icon: ChartDonut },
                { id: 'bar', icon: ChartBar },
              ].map(ct => (
                <button key={ct.id} onClick={() => setExpenseChartType(ct.id)} data-testid={`expense-chart-${ct.id}`}
                  className="p-1.5 rounded-md transition-colors"
                  style={{ background: expenseChartType === ct.id ? 'var(--app-accent)' : 'transparent', color: expenseChartType === ct.id ? '#fff' : 'var(--app-text-muted)' }}>
                  <ct.icon size={14} />
                </button>
              ))}
            </div>
          </div>
          {expenseData.length > 0 ? (
            <div>
              {expenseChartType === 'pie' ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={expenseData} cx="50%" cy="50%" outerRadius={80} innerRadius={40}
                      dataKey="amount" nameKey="category" isAnimationActive={false}
                      label={renderPieLabel} labelLine={false}
                      onClick={(_, idx) => {
                        const cat = expenseData[idx];
                        if (cat) goToTransactions({ search: cat.category, type: 'debit' });
                      }}
                      className="cursor-pointer">
                      {expenseData.map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v, name) => {
                      const pct = totalExpenseSum > 0 ? ((v / totalExpenseSum) * 100).toFixed(1) : 0;
                      return [`₹${v.toFixed(2)} (${pct}%)`, name];
                    }}
                      contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={[...expenseData].sort((a, b) => b.amount - a.amount).slice(0, 10)}
                    onClick={(data) => {
                      if (data?.activePayload?.[0]) {
                        const cat = data.activePayload[0].payload.category;
                        goToTransactions({ search: cat, type: 'debit' });
                      }
                    }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--app-card-border)" />
                    <XAxis dataKey="category" style={{ fontSize: '9px' }} tick={{ fill: 'var(--app-text-muted)' }}
                      tickFormatter={v => v.length > 8 ? v.slice(0, 7) + '..' : v} />
                    <YAxis style={{ fontSize: '10px' }} tick={{ fill: 'var(--app-text-muted)' }}
                      tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                    <Tooltip formatter={(v, name) => {
                      const pct = totalExpenseSum > 0 ? ((v / totalExpenseSum) * 100).toFixed(1) : 0;
                      return [`₹${v.toFixed(2)} (${pct}%)`, name];
                    }}
                      contentStyle={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)', borderRadius: '8px', fontSize: '12px' }} />
                    <Bar dataKey="amount" radius={[4, 4, 0, 0]} className="cursor-pointer">
                      {[...expenseData].sort((a, b) => b.amount - a.amount).slice(0, 10).map((e, i) => <Cell key={i} fill={e.fill || COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
              <div className="mt-2 space-y-1.5 max-h-[100px] overflow-y-auto">
                {[...expenseData].sort((a, b) => b.amount - a.amount).map((e, i) => {
                  const pct = totalExpenseSum > 0 ? ((e.amount / totalExpenseSum) * 100).toFixed(1) : 0;
                  return (
                    <div key={i} className="flex items-center justify-between text-xs cursor-pointer hover:opacity-80 transition-opacity"
                      onClick={() => goToTransactions({ search: e.category, type: 'debit' })}
                      data-testid={`category-legend-${i}`}>
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: e.fill || COLORS[i % COLORS.length] }} />
                        <span className="truncate" style={{ color: 'var(--app-text-secondary)' }}>{e.category}</span>
                      </div>
                      <div className="shrink-0 ml-2 flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'var(--app-card-border)', color: 'var(--app-text-muted)' }}>{pct}%</span>
                        <span className="font-medium" style={{ color: 'var(--app-text)' }}>
                          ₹{e.amount >= 1000 ? `${(e.amount/1000).toFixed(1)}k` : e.amount.toFixed(0)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : <p className="text-center py-12 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense data yet</p>}
        </div>
      </div>

      {/* Trend Chart with type selector */}
      {trendData.length > 0 && (
        <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading text-base" style={{ color: 'var(--app-text)' }}>
              {isSingleMonth ? 'Daily Trend' : 'Monthly Trend'}
            </h3>
            <div className="flex gap-1" data-testid="trend-chart-type-selector">
              {CHART_TYPES.map(ct => (
                <button key={ct.id} onClick={() => setTrendChartType(ct.id)} data-testid={`trend-chart-${ct.id}`}
                  className="flex items-center gap-1 px-2 py-1.5 rounded-md text-[11px] font-medium transition-colors"
                  style={{
                    background: trendChartType === ct.id ? 'var(--app-accent)' : 'transparent',
                    color: trendChartType === ct.id ? '#fff' : 'var(--app-text-muted)',
                    border: `1px solid ${trendChartType === ct.id ? 'var(--app-accent)' : 'var(--app-card-border)'}`,
                  }}>
                  <ct.icon size={13} /> {ct.label}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            {renderTrendChart()}
          </ResponsiveContainer>
        </div>
      )}

      {/* Top Creditors & Debitors Row - Clickable */}
      {((analytics?.top_creditors?.length > 0) || (analytics?.top_debitors?.length > 0)) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {analytics?.top_debitors?.length > 0 && (
            <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
              <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Spends</h3>
              <div className="space-y-2">
                {analytics.top_debitors.slice(0, 8).map((d, i) => (
                  <div key={i} data-testid={`top-debitor-${i}`}
                    className="flex items-center justify-between py-1.5 cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => goToTransactions({ search: d.description, type: 'debit' })}>
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

          {analytics?.top_creditors?.length > 0 && (
            <div className="rounded-lg p-5 shadow-sm" style={{ background: 'var(--app-card-bg)', border: '1px solid var(--app-card-border)' }}>
              <h3 className="font-heading text-base mb-3" style={{ color: 'var(--app-text)' }}>Top Income Sources</h3>
              <div className="space-y-2">
                {analytics.top_creditors.slice(0, 8).map((c, i) => (
                  <div key={i} data-testid={`top-creditor-${i}`}
                    className="flex items-center justify-between py-1.5 cursor-pointer hover:opacity-80 transition-opacity"
                    onClick={() => goToTransactions({ search: c.description, type: 'credit' })}>
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
              <div key={i} data-testid={`account-summary-${a.name}`} className="p-4 rounded-lg cursor-pointer hover:shadow-md transition-all"
                onClick={() => goToTransactions({ search: a.name })}
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
