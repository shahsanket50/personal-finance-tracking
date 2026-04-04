import { useState, useEffect } from 'react';
import axios from 'axios';
import { Scales, ArrowUp, ArrowDown } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const TrialBalance = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => { loadData(); }, []);

  const loadData = async (sd, ed) => {
    setLoading(true);
    try {
      let url = `${API}/trial-balance`;
      const params = [];
      if (sd) params.push(`start_date=${sd}`);
      if (ed) params.push(`end_date=${ed}`);
      if (params.length) url += '?' + params.join('&');
      const res = await axios.get(url);
      setData(res.data);
    } catch {
      toast.error('Failed to load trial balance');
    } finally {
      setLoading(false);
    }
  };

  const applyFilter = () => loadData(startDate, endDate);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="trial-balance-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Trial Balance</h1>
          <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>
            {data?.is_balanced ? (
              <span style={{ color: '#5C745A' }}>Balanced</span>
            ) : (
              <span style={{ color: '#C06B52' }}>Not balanced — difference: {Math.abs((data?.total_debit || 0) - (data?.total_credit || 0)).toLocaleString('en-IN')}</span>
            )}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <Label className="text-xs">From</Label>
          <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" data-testid="tb-start-date" />
        </div>
        <div>
          <Label className="text-xs">To</Label>
          <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" data-testid="tb-end-date" />
        </div>
        <button onClick={applyFilter} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--app-accent)' }} data-testid="tb-filter-btn">Filter</button>
      </div>

      <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
        {(!data || data.rows.length === 0) ? (
          <div className="p-8 text-center" style={{ color: 'var(--app-text-muted)' }}>
            <Scales size={40} className="mx-auto mb-2 opacity-40" />
            <p>No entries to show</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'var(--app-bg)' }}>
                  <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--app-text-muted)' }}>Ledger</th>
                  <th className="text-left px-4 py-3 font-medium" style={{ color: 'var(--app-text-muted)' }}>Group</th>
                  <th className="text-center px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: 'var(--app-text-muted)' }}>Nature</th>
                  <th className="text-right px-4 py-3 font-medium" style={{ color: '#5C745A' }}>Debit</th>
                  <th className="text-right px-4 py-3 font-medium" style={{ color: '#C06B52' }}>Credit</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row, i) => (
                  <tr key={i} className="border-t hover:bg-black/[0.02] transition-colors" style={{ borderColor: 'var(--app-border)' }}>
                    <td className="px-4 py-2.5 font-medium" style={{ color: 'var(--app-text)' }}>{row.ledger_name}</td>
                    <td className="px-4 py-2.5" style={{ color: 'var(--app-text-muted)' }}>{row.group_name}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wider"
                        style={{ background: row.nature === 'asset' || row.nature === 'expense' ? '#5C745A15' : '#C06B5215', color: row.nature === 'asset' || row.nature === 'expense' ? '#5C745A' : '#C06B52' }}>
                        {row.nature}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: '#5C745A' }}>
                      {row.debit > 0 ? row.debit.toLocaleString('en-IN') : '-'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono" style={{ color: '#C06B52' }}>
                      {row.credit > 0 ? row.credit.toLocaleString('en-IN') : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--app-text-muted)' }}>
                  <td className="px-4 py-3" colSpan={3} style={{ color: 'var(--app-text)' }}>Total</td>
                  <td className="px-4 py-3 text-right font-mono" style={{ color: '#5C745A' }}>{data.total_debit.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-3 text-right font-mono" style={{ color: '#C06B52' }}>{data.total_credit.toLocaleString('en-IN')}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrialBalance;
