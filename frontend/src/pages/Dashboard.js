import { useState, useEffect } from 'react';
import axios from 'axios';
import { Wallet, TrendUp, TrendDown, ArrowsLeftRight, DownloadSimple } from '@phosphor-icons/react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [accounts, setAccounts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

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
      console.error(err);
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
      toast.success('Backup downloaded successfully');
    } catch (err) {
      toast.error('Failed to export backup');
    }
  };

  if (loading) {
    return <div className="text-center py-12" style={{ color: '#78716C' }}>Loading...</div>;
  }

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.current_balance, 0);
  const expenseData = analytics?.category_breakdown?.filter(c => c.type === 'expense') || [];
  const incomeData = analytics?.category_breakdown?.filter(c => c.type === 'income') || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
            Dashboard
          </h2>
          <p className="text-sm mt-1" style={{ color: '#78716C' }}>Overview of your financial health</p>
        </div>
        <Button
          onClick={handleExportBackup}
          data-testid="export-backup-btn"
          className="bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
        >
          <DownloadSimple size={18} className="mr-2" />
          Export Backup
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
        <div 
          data-testid="total-balance-card"
          className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Total Balance</span>
            <Wallet size={20} style={{ color: '#5C745A' }} />
          </div>
          <div className="font-heading text-3xl" style={{ color: '#1C1917' }}>₹{totalBalance.toFixed(2)}</div>
        </div>

        <div 
          data-testid="total-income-card"
          className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Income</span>
            <TrendUp size={20} style={{ color: '#5C745A' }} />
          </div>
          <div className="font-heading text-3xl" style={{ color: '#5C745A' }}>₹{analytics?.total_income?.toFixed(2) || 0}</div>
        </div>

        <div 
          data-testid="total-expense-card"
          className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Expenses</span>
            <TrendDown size={20} style={{ color: '#C06B52' }} />
          </div>
          <div className="font-heading text-3xl" style={{ color: '#C06B52' }}>₹{analytics?.total_expense?.toFixed(2) || 0}</div>
        </div>

        <div 
          data-testid="net-savings-card"
          className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Net Savings</span>
            <ArrowsLeftRight size={20} style={{ color: '#7CA1A6' }} />
          </div>
          <div className="font-heading text-3xl" style={{ color: analytics?.net_savings >= 0 ? '#5C745A' : '#C06B52' }}>
            ₹{analytics?.net_savings?.toFixed(2) || 0}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expense Breakdown */}
        <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
          <h3 className="font-heading text-xl mb-4" style={{ color: '#1C1917' }}>Expense Breakdown</h3>
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
            <p className="text-center py-12" style={{ color: '#A8A29E' }}>No expense data available</p>
          )}
        </div>

        {/* Monthly Trend */}
        <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
          <h3 className="font-heading text-xl mb-4" style={{ color: '#1C1917' }}>Monthly Trend</h3>
          {analytics?.monthly_trend?.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E2DC" />
                <XAxis dataKey="month" style={{ fontSize: '12px' }} />
                <YAxis style={{ fontSize: '12px' }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="income" fill="#5C745A" name="Income" />
                <Bar dataKey="expense" fill="#C06B52" name="Expense" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center py-12" style={{ color: '#A8A29E' }}>No monthly data available</p>
          )}
        </div>
      </div>

      {/* Accounts Overview */}
      <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
        <h3 className="font-heading text-xl mb-4" style={{ color: '#1C1917' }}>Accounts</h3>
        {accounts.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {accounts.map(account => (
              <div 
                key={account.id} 
                data-testid={`account-${account.name}`}
                className="p-4 border border-[#E5E2DC] rounded-lg"
              >
                <div className="text-xs uppercase tracking-[0.2em] mb-1" style={{ color: '#78716C' }}>
                  {account.account_type.replace('_', ' ')}
                </div>
                <div className="font-medium mb-1" style={{ color: '#1C1917' }}>{account.name}</div>
                <div className="text-lg font-heading" style={{ color: '#5C745A' }}>
                  ₹{account.current_balance.toFixed(2)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center py-6" style={{ color: '#A8A29E' }}>No accounts yet. Create one to get started!</p>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
