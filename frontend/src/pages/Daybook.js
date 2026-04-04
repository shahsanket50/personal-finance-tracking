import { useState, useEffect } from 'react';
import axios from 'axios';
import { BookOpen, CalendarBlank } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const TYPE_COLORS = {
  payment: '#C06B52', receipt: '#5C745A', journal: '#7CA1A6',
  contra: '#D4A373', sales: '#5C745A', purchase: '#C06B52',
  credit_note: '#7CA1A6', debit_note: '#D4A373',
};

const Daybook = () => {
  const [vouchers, setVouchers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => { loadData(); }, []);

  const loadData = async (sd, ed) => {
    setLoading(true);
    try {
      let url = `${API}/daybook`;
      const params = [];
      if (sd) params.push(`start_date=${sd}`);
      if (ed) params.push(`end_date=${ed}`);
      if (params.length) url += '?' + params.join('&');
      const res = await axios.get(url);
      setVouchers(res.data);
    } catch {
      toast.error('Failed to load daybook');
    } finally {
      setLoading(false);
    }
  };

  const applyFilter = () => { loadData(startDate, endDate); };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="daybook-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Daybook</h1>
          <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>Journal of all voucher entries</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <Label className="text-xs">From</Label>
          <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" data-testid="daybook-start-date" />
        </div>
        <div>
          <Label className="text-xs">To</Label>
          <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" data-testid="daybook-end-date" />
        </div>
        <button onClick={applyFilter} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--app-accent)' }} data-testid="daybook-filter-btn">
          Filter
        </button>
      </div>

      <div className="space-y-3">
        {vouchers.length === 0 ? (
          <div className="border rounded-lg p-8 text-center" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)', color: 'var(--app-text-muted)' }}>
            <BookOpen size={40} className="mx-auto mb-2 opacity-40" />
            <p>No entries found for this period</p>
          </div>
        ) : (
          vouchers.map(v => (
            <div key={v.id} className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }} data-testid={`daybook-entry-${v.id}`}>
              <div className="flex items-center gap-3 px-4 py-2.5 border-b" style={{ borderColor: 'var(--app-border)', background: 'var(--app-bg)' }}>
                <span className="text-xs font-mono" style={{ color: 'var(--app-text-muted)' }}>{v.voucher_number}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase" style={{ background: `${TYPE_COLORS[v.voucher_type] || '#78716C'}15`, color: TYPE_COLORS[v.voucher_type] || '#78716C' }}>
                  {v.voucher_type}
                </span>
                <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--app-text-muted)' }}>
                  <CalendarBlank size={12} /> {v.date}
                </span>
                {v.narration && <span className="text-xs flex-1 truncate" style={{ color: 'var(--app-text)' }}>{v.narration}</span>}
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {v.entries?.map((e, i) => (
                    <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                      <td className="px-4 py-1.5" style={{ color: 'var(--app-text)', paddingLeft: e.credit > 0 ? '2.5rem' : '1rem' }}>
                        {e.ledger_name || 'Unknown'}
                      </td>
                      <td className="px-4 py-1.5 text-right font-mono w-28" style={{ color: '#5C745A' }}>
                        {e.debit > 0 ? e.debit.toLocaleString('en-IN') : ''}
                      </td>
                      <td className="px-4 py-1.5 text-right font-mono w-28" style={{ color: '#C06B52' }}>
                        {e.credit > 0 ? e.credit.toLocaleString('en-IN') : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Daybook;
