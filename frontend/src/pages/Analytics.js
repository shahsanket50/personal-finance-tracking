import { useState, useEffect } from 'react';
import axios from 'axios';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Button } from '../components/ui/button';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line } from 'recharts';
import { toast } from 'sonner';
import { CalendarBlank } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [period, setPeriod] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async (start = '', end = '') => {
    setLoading(true);
    try {
      let url = `${API}/analytics/summary`;
      if (start && end) {
        url += `?start_date=${start}&end_date=${end}`;
      }
      const res = await axios.get(url);
      setAnalytics(res.data);
    } catch (err) {
      toast.error('Failed to load analytics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodChange = (value) => {
    setPeriod(value);
    const today = new Date();
    let start, end;

    switch(value) {
      case 'this_month':
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'last_month':
        start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        end = new Date(today.getFullYear(), today.getMonth(), 0);
        break;
      case 'this_fy':
        // Financial year starts from April
        const fyStart = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
        start = new Date(fyStart, 3, 1); // April 1
        end = new Date(fyStart + 1, 2, 31); // March 31
        break;
      case 'last_fy':
        const lastFyStart = today.getMonth() >= 3 ? today.getFullYear() - 1 : today.getFullYear() - 2;
        start = new Date(lastFyStart, 3, 1);
        end = new Date(lastFyStart + 1, 2, 31);
        break;
      case 'custom':
        return; // Don't auto-load for custom
      default:
        loadAnalytics();
        return;
    }

    const startStr = start.toISOString().split('T')[0];
    const endStr = end.toISOString().split('T')[0];
    setStartDate(startStr);
    setEndDate(endStr);
    loadAnalytics(startStr, endStr);
  };

  const handleCustomDateSubmit = () => {
    if (startDate && endDate) {
      loadAnalytics(startDate, endDate);
    } else {
      toast.error('Please select both start and end dates');
    }
  };

  if (loading) {
    return <div className="text-center py-12" style={{ color: 'var(--app-text-secondary)' }}>Loading analytics...</div>;
  }

  const expenseData = analytics?.category_breakdown?.filter(c => c.type === 'expense') || [];
  const incomeData = analytics?.category_breakdown?.filter(c => c.type === 'income') || [];
  const topExpenses = [...expenseData].sort((a, b) => b.amount - a.amount).slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--app-text)' }}>
            Analytics
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Deep dive into your financial patterns</p>
        </div>
      </div>

      {/* Period Selection */}
      <div className="themed-card rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-3 mb-4">
          <CalendarBlank size={20} style={{ color: 'var(--app-accent)' }} />
          <h3 className="font-heading text-lg" style={{ color: 'var(--app-text)' }}>Select Period</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <Label>Period</Label>
            <Select value={period} onValueChange={handlePeriodChange}>
              <SelectTrigger data-testid="period-select">
                <SelectValue />
              </SelectTrigger>
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
              <div>
                <Label>Start Date</Label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  data-testid="start-date-input"
                  className="w-full mt-1 p-2 border border-[var(--app-card-border)] rounded-lg"
                  style={{ color: 'var(--app-text)' }}
                />
              </div>
              <div>
                <Label>End Date</Label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  data-testid="end-date-input"
                  className="w-full mt-1 p-2 border border-[var(--app-card-border)] rounded-lg"
                  style={{ color: 'var(--app-text)' }}
                />
              </div>
              <div className="flex items-end">
                <Button
                  onClick={handleCustomDateSubmit}
                  data-testid="apply-date-range-btn"
                  className="w-full themed-btn-primary rounded-lg"
                >
                  Apply
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="themed-card rounded-lg p-6 shadow-sm">
          <div className="text-xs uppercase tracking-[0.2em] mb-2" style={{ color: 'var(--app-text-secondary)' }}>Total Income</div>
          <div className="font-heading text-3xl" style={{ color: 'var(--app-accent)' }}>
            ₹{analytics?.total_income?.toFixed(2) || 0}
          </div>
        </div>
        <div className="themed-card rounded-lg p-6 shadow-sm">
          <div className="text-xs uppercase tracking-[0.2em] mb-2" style={{ color: 'var(--app-text-secondary)' }}>Total Expenses</div>
          <div className="font-heading text-3xl" style={{ color: 'var(--app-danger)' }}>
            ₹{analytics?.total_expense?.toFixed(2) || 0}
          </div>
        </div>
        <div className="themed-card rounded-lg p-6 shadow-sm">
          <div className="text-xs uppercase tracking-[0.2em] mb-2" style={{ color: 'var(--app-text-secondary)' }}>Net Savings</div>
          <div className="font-heading text-3xl" style={{ color: analytics?.net_savings >= 0 ? '#5C745A' : '#C06B52' }}>
            ₹{analytics?.net_savings?.toFixed(2) || 0}
          </div>
        </div>
        <div className="themed-card rounded-lg p-6 shadow-sm">
          <div className="text-xs uppercase tracking-[0.2em] mb-2" style={{ color: 'var(--app-text-secondary)' }}>Savings Rate</div>
          <div className="font-heading text-3xl" style={{ color: '#7CA1A6' }}>
            {analytics?.total_income > 0 ? ((analytics.net_savings / analytics.total_income) * 100).toFixed(1) : 0}%
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income vs Expense Pie Charts */}
        <div className="themed-card rounded-lg p-6 shadow-sm">
          <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Income Breakdown</h3>
          {incomeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={incomeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="amount"
                >
                  {incomeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No income data</p>
          )}
        </div>

        <div className="themed-card rounded-lg p-6 shadow-sm">
          <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Expense Breakdown</h3>
          {expenseData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={expenseData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="amount"
                >
                  {expenseData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No expense data</p>
          )}
        </div>
      </div>

      {/* Monthly Trend */}
      <div className="themed-card rounded-lg p-6 shadow-sm">
        <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Monthly Trend</h3>
        {analytics?.monthly_trend?.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={analytics.monthly_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E2DC" />
              <XAxis dataKey="month" style={{ fontSize: '12px' }} />
              <YAxis style={{ fontSize: '12px' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="income" stroke="#5C745A" strokeWidth={2} name="Income" />
              <Line type="monotone" dataKey="expense" stroke="#C06B52" strokeWidth={2} name="Expense" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No monthly data</p>
        )}
      </div>

      {/* Top Expenses */}
      <div className="themed-card rounded-lg p-6 shadow-sm">
        <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Top 5 Expense Categories</h3>
        {topExpenses.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topExpenses} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E2DC" />
              <XAxis type="number" style={{ fontSize: '12px' }} />
              <YAxis dataKey="category" type="category" width={150} style={{ fontSize: '12px' }} />
              <Tooltip />
              <Bar dataKey="amount" fill="#C06B52" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-center py-12" style={{ color: 'var(--app-text-muted)' }}>No expense data</p>
        )}
      </div>

      {/* Account Balances */}
      <div className="themed-card rounded-lg p-6 shadow-sm">
        <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Account Balances</h3>
        {analytics?.account_balances?.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {analytics.account_balances.map((acc, idx) => (
              <div key={idx} className="p-4 border border-[var(--app-card-border)] rounded-lg">
                <div className="text-xs uppercase tracking-[0.2em] mb-1" style={{ color: 'var(--app-text-secondary)' }}>
                  {acc.type.replace('_', ' ')}
                </div>
                <div className="font-medium mb-1" style={{ color: 'var(--app-text)' }}>{acc.name}</div>
                <div className="text-lg font-heading" style={{ color: 'var(--app-accent)' }}>
                  ₹{acc.balance.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center py-6" style={{ color: 'var(--app-text-muted)' }}>No account data</p>
        )}
      </div>
    </div>
  );
};

export default Analytics;
