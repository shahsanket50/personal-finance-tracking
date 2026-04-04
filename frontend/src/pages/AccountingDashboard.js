import { useState, useEffect } from 'react';
import axios from 'axios';
import { Buildings, Scales, BookOpen, Receipt, ChartBar, CalendarBlank, Gear } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const AccountingDashboard = () => {
  const [company, setCompany] = useState(null);
  const [stats, setStats] = useState({ ledgers: 0, vouchers: 0, groups: 0 });
  const [trialBalance, setTrialBalance] = useState(null);
  const [profitLoss, setProfitLoss] = useState(null);
  const [currentFy, setCurrentFy] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [companyRes, ledgersRes, vouchersRes, groupsRes, tbRes, plRes, fyRes] = await Promise.all([
        axios.get(`${API}/company`),
        axios.get(`${API}/ledgers`),
        axios.get(`${API}/vouchers`),
        axios.get(`${API}/account-groups`),
        axios.get(`${API}/trial-balance`),
        axios.get(`${API}/profit-loss`),
        axios.get(`${API}/financial-years`),
      ]);
      setCompany(companyRes.data);
      setStats({
        ledgers: ledgersRes.data.length,
        vouchers: vouchersRes.data.length,
        groups: groupsRes.data.length,
      });
      setTrialBalance(tbRes.data);
      setProfitLoss(plRes.data);
      setCurrentFy(fyRes.data.current_fy || '');
    } catch {
      toast.error('Failed to load accounting data');
    } finally {
      setLoading(false);
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
            {company?.gstin ? `GSTIN: ${company.gstin}` : ''}
            {company?.pan ? `${company?.gstin ? ' | ' : ''}PAN: ${company.pan}` : ''}
            {currentFy && <span className="ml-2 px-2 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>
              <CalendarBlank size={12} className="inline mr-1" />{currentFy}
            </span>}
          </p>
        </div>
        <button
          onClick={() => navigate('/settings')}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors border"
          style={{ borderColor: 'var(--app-border)', color: 'var(--app-text-muted)', background: 'var(--app-surface)' }}
          data-testid="company-settings-link"
        >
          <Gear size={16} /> Company Settings
        </button>
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
