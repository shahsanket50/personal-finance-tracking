import { useState, useEffect } from 'react';
import axios from 'axios';
import { ChartLine, TrendUp, TrendDown, Scales } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Reports = () => {
  const [activeReport, setActiveReport] = useState('pl');
  const [plData, setPlData] = useState(null);
  const [bsData, setBsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [asOfDate, setAsOfDate] = useState('');

  useEffect(() => { loadReport(); }, [activeReport]);

  const loadReport = async () => {
    setLoading(true);
    try {
      if (activeReport === 'pl') {
        let url = `${API}/profit-loss`;
        const params = [];
        if (startDate) params.push(`start_date=${startDate}`);
        if (endDate) params.push(`end_date=${endDate}`);
        if (params.length) url += '?' + params.join('&');
        const res = await axios.get(url);
        setPlData(res.data);
      } else {
        let url = `${API}/balance-sheet`;
        if (asOfDate) url += `?as_of_date=${asOfDate}`;
        const res = await axios.get(url);
        setBsData(res.data);
      }
    } catch {
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const renderPL = () => {
    if (!plData) return null;
    return (
      <div className="space-y-4" data-testid="pl-report">
        <div className="grid grid-cols-3 gap-4">
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <TrendUp size={18} style={{ color: '#5C745A' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Income</span>
            </div>
            <p className="text-xl font-bold" style={{ color: '#5C745A' }}>{plData.total_income.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <TrendDown size={18} style={{ color: '#C06B52' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Expenses</span>
            </div>
            <p className="text-xl font-bold" style={{ color: '#C06B52' }}>{plData.total_expenses.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <Scales size={18} style={{ color: plData.net_profit >= 0 ? '#5C745A' : '#C06B52' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Net {plData.net_profit >= 0 ? 'Profit' : 'Loss'}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: plData.net_profit >= 0 ? '#5C745A' : '#C06B52' }}>
              {plData.net_profit.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Income */}
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#5C745A08' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#5C745A' }}>Income</h3>
            </div>
            {plData.income.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No income entries</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {plData.income.map((item, i) => (
                    <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                      <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>{item.ledger_name}</td>
                      <td className="px-4 py-2 text-right font-mono" style={{ color: '#5C745A' }}>{item.amount.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 font-bold" style={{ borderColor: '#5C745A' }}>
                    <td className="px-4 py-2" style={{ color: '#5C745A' }}>Total</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#5C745A' }}>{plData.total_income.toLocaleString('en-IN')}</td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>

          {/* Expenses */}
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#C06B5208' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#C06B52' }}>Expenses</h3>
            </div>
            {plData.expenses.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No expense entries</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {plData.expenses.map((item, i) => (
                    <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                      <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>{item.ledger_name}</td>
                      <td className="px-4 py-2 text-right font-mono" style={{ color: '#C06B52' }}>{item.amount.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 font-bold" style={{ borderColor: '#C06B52' }}>
                    <td className="px-4 py-2" style={{ color: '#C06B52' }}>Total</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#C06B52' }}>{plData.total_expenses.toLocaleString('en-IN')}</td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderBS = () => {
    if (!bsData) return null;
    return (
      <div className="space-y-4" data-testid="bs-report">
        <div className="grid grid-cols-3 gap-4">
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Assets</span>
            <p className="text-xl font-bold" style={{ color: '#5C745A' }}>{bsData.total_assets.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Liabilities</span>
            <p className="text-xl font-bold" style={{ color: '#C06B52' }}>{bsData.total_liabilities.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Status</span>
            <p className="text-xl font-bold" style={{ color: bsData.is_balanced ? '#5C745A' : '#C06B52' }}>
              {bsData.is_balanced ? 'Balanced' : 'Unbalanced'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Assets */}
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#5C745A08' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#5C745A' }}>Assets</h3>
            </div>
            {bsData.assets.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No assets</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {bsData.assets.map((item, i) => (
                    <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                      <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>{item.ledger_name}</td>
                      <td className="px-4 py-2 text-right font-mono" style={{ color: '#5C745A' }}>{item.amount.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 font-bold" style={{ borderColor: '#5C745A' }}>
                    <td className="px-4 py-2" style={{ color: '#5C745A' }}>Total</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#5C745A' }}>{bsData.total_assets.toLocaleString('en-IN')}</td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>

          {/* Liabilities */}
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#C06B5208' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#C06B52' }}>Liabilities & Capital</h3>
            </div>
            {bsData.liabilities.length === 0 ? (
              <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No liabilities</p>
            ) : (
              <table className="w-full text-sm">
                <tbody>
                  {bsData.liabilities.map((item, i) => (
                    <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                      <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>{item.ledger_name}</td>
                      <td className="px-4 py-2 text-right font-mono" style={{ color: '#C06B52' }}>{item.amount.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 font-bold" style={{ borderColor: '#C06B52' }}>
                    <td className="px-4 py-2" style={{ color: '#C06B52' }}>Total</td>
                    <td className="px-4 py-2 text-right font-mono" style={{ color: '#C06B52' }}>{bsData.total_liabilities.toLocaleString('en-IN')}</td>
                  </tr>
                </tfoot>
              </table>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4" data-testid="reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Financial Reports</h1>
        </div>
      </div>

      {/* Report Tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveReport('pl')}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: activeReport === 'pl' ? 'var(--app-accent)' : 'var(--app-surface)',
            color: activeReport === 'pl' ? 'white' : 'var(--app-text-muted)',
            border: `1px solid ${activeReport === 'pl' ? 'var(--app-accent)' : 'var(--app-border)'}`,
          }}
          data-testid="tab-pl"
        >
          <ChartLine size={16} className="inline mr-1.5" /> Profit & Loss
        </button>
        <button
          onClick={() => setActiveReport('bs')}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: activeReport === 'bs' ? 'var(--app-accent)' : 'var(--app-surface)',
            color: activeReport === 'bs' ? 'white' : 'var(--app-text-muted)',
            border: `1px solid ${activeReport === 'bs' ? 'var(--app-accent)' : 'var(--app-border)'}`,
          }}
          data-testid="tab-bs"
        >
          <Scales size={16} className="inline mr-1.5" /> Balance Sheet
        </button>
      </div>

      {/* Date Filters */}
      {activeReport === 'pl' ? (
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <Label className="text-xs">From</Label>
            <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" />
          </div>
          <div>
            <Label className="text-xs">To</Label>
            <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" />
          </div>
          <button onClick={loadReport} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--app-accent)' }} data-testid="report-filter-btn">Filter</button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <Label className="text-xs">As of Date</Label>
            <Input type="date" value={asOfDate} onChange={e => setAsOfDate(e.target.value)} className="w-40" />
          </div>
          <button onClick={loadReport} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--app-accent)' }} data-testid="report-filter-btn">Filter</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
        </div>
      ) : (
        activeReport === 'pl' ? renderPL() : renderBS()
      )}
    </div>
  );
};

export default Reports;
