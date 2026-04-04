import { useState, useEffect } from 'react';
import axios from 'axios';
import { Receipt, Plus, Trash, Funnel, MagnifyingGlass } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const VOUCHER_TYPES = [
  { value: 'payment', label: 'Payment', color: '#C06B52' },
  { value: 'receipt', label: 'Receipt', color: '#5C745A' },
  { value: 'journal', label: 'Journal', color: '#7CA1A6' },
  { value: 'contra', label: 'Contra', color: '#D4A373' },
  { value: 'sales', label: 'Sales', color: '#5C745A' },
  { value: 'purchase', label: 'Purchase', color: '#C06B52' },
  { value: 'credit_note', label: 'Credit Note', color: '#7CA1A6' },
  { value: 'debit_note', label: 'Debit Note', color: '#D4A373' },
];

const TYPE_MAP = Object.fromEntries(VOUCHER_TYPES.map(t => [t.value, t]));

const Vouchers = () => {
  const [vouchers, setVouchers] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [filterType, setFilterType] = useState('all');
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({
    voucher_type: 'payment',
    date: new Date().toISOString().slice(0, 10),
    narration: '',
    reference: '',
    entries: [
      { ledger_id: '', debit: 0, credit: 0 },
      { ledger_id: '', debit: 0, credit: 0 },
    ],
  });

  useEffect(() => { loadData(); }, [filterType]);

  const loadData = async () => {
    setLoading(true);
    try {
      const params = filterType !== 'all' ? `?voucher_type=${filterType}` : '';
      const [vRes, lRes] = await Promise.all([
        axios.get(`${API}/vouchers${params}`),
        axios.get(`${API}/ledgers`),
      ]);
      setVouchers(vRes.data);
      setLedgers(lRes.data);
    } catch {
      toast.error('Failed to load vouchers');
    } finally {
      setLoading(false);
    }
  };

  const ledgerMap = Object.fromEntries(ledgers.map(l => [l.id, l.name]));

  const addEntry = () => {
    setForm(p => ({
      ...p,
      entries: [...p.entries, { ledger_id: '', debit: 0, credit: 0 }],
    }));
  };

  const removeEntry = (idx) => {
    if (form.entries.length <= 2) return;
    setForm(p => ({
      ...p,
      entries: p.entries.filter((_, i) => i !== idx),
    }));
  };

  const updateEntry = (idx, field, value) => {
    setForm(p => ({
      ...p,
      entries: p.entries.map((e, i) => i === idx ? { ...e, [field]: field === 'ledger_id' ? value : (parseFloat(value) || 0) } : e),
    }));
  };

  const totalDebit = form.entries.reduce((s, e) => s + (e.debit || 0), 0);
  const totalCredit = form.entries.reduce((s, e) => s + (e.credit || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01;

  const createVoucher = async () => {
    if (!isBalanced) return toast.error('Voucher must be balanced (Dr = Cr)');
    if (form.entries.some(e => !e.ledger_id)) return toast.error('All entries must have a ledger');
    if (totalDebit === 0) return toast.error('Amount cannot be zero');
    try {
      await axios.post(`${API}/vouchers`, form);
      toast.success('Voucher created');
      setCreateOpen(false);
      setForm({
        voucher_type: 'payment', date: new Date().toISOString().slice(0, 10),
        narration: '', reference: '',
        entries: [{ ledger_id: '', debit: 0, credit: 0 }, { ledger_id: '', debit: 0, credit: 0 }],
      });
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create voucher');
    }
  };

  const deleteVoucher = async (id) => {
    if (!window.confirm('Delete this voucher?')) return;
    try {
      await axios.delete(`${API}/vouchers/${id}`);
      toast.success('Voucher deleted');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete');
    }
  };

  const filtered = vouchers.filter(v =>
    !search || v.narration?.toLowerCase().includes(search.toLowerCase()) || v.voucher_number?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="vouchers-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Vouchers</h1>
          <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>{filtered.length} voucher{filtered.length !== 1 ? 's' : ''}</p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)} data-testid="create-voucher-btn">
          <Plus size={16} className="mr-1" /> New Voucher
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setFilterType('all')}
            className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
            style={{
              background: filterType === 'all' ? 'var(--app-accent)' : 'var(--app-surface)',
              color: filterType === 'all' ? 'white' : 'var(--app-text-muted)',
              border: `1px solid ${filterType === 'all' ? 'var(--app-accent)' : 'var(--app-border)'}`,
            }}
            data-testid="filter-all"
          >
            All
          </button>
          {VOUCHER_TYPES.map(t => (
            <button
              key={t.value}
              onClick={() => setFilterType(t.value)}
              className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
              style={{
                background: filterType === t.value ? t.color : 'var(--app-surface)',
                color: filterType === t.value ? 'white' : 'var(--app-text-muted)',
                border: `1px solid ${filterType === t.value ? t.color : 'var(--app-border)'}`,
              }}
              data-testid={`filter-${t.value}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--app-text-muted)' }} />
          <Input
            placeholder="Search narration, voucher #..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9"
            data-testid="search-vouchers"
          />
        </div>
      </div>

      {/* Voucher List */}
      <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
        {filtered.length === 0 ? (
          <div className="p-8 text-center" style={{ color: 'var(--app-text-muted)' }}>
            <Receipt size={40} className="mx-auto mb-2 opacity-40" />
            <p>No vouchers found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'var(--app-bg)' }}>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Voucher #</th>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Date</th>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Type</th>
                  <th className="text-left px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Particulars</th>
                  <th className="text-right px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}>Amount</th>
                  <th className="text-right px-4 py-2.5 font-medium" style={{ color: 'var(--app-text-muted)' }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(v => {
                  const typeInfo = TYPE_MAP[v.voucher_type] || { label: v.voucher_type, color: '#78716C' };
                  const amount = v.entries?.reduce((s, e) => s + (e.debit || 0), 0) || 0;
                  const particulars = v.entries?.map(e => ledgerMap[e.ledger_id] || 'Unknown').join(' / ') || '';
                  return (
                    <tr key={v.id} className="border-t hover:bg-black/[0.02] transition-colors" style={{ borderColor: 'var(--app-border)' }} data-testid={`voucher-row-${v.id}`}>
                      <td className="px-4 py-2.5 font-mono text-xs" style={{ color: 'var(--app-text)' }}>{v.voucher_number}</td>
                      <td className="px-4 py-2.5" style={{ color: 'var(--app-text)' }}>{v.date}</td>
                      <td className="px-4 py-2.5">
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium" style={{ background: `${typeInfo.color}15`, color: typeInfo.color }}>
                          {typeInfo.label}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 max-w-[300px] truncate" style={{ color: 'var(--app-text-muted)' }}>
                        {v.narration || particulars}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono" style={{ color: 'var(--app-text)' }}>
                        {amount.toLocaleString('en-IN')}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {!v.linked_transaction_id && (
                          <button onClick={() => deleteVoucher(v.id)} className="p-1 rounded hover:bg-black/5" data-testid={`delete-voucher-${v.id}`}>
                            <Trash size={14} style={{ color: '#C06B52' }} />
                          </button>
                        )}
                        {v.linked_transaction_id && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>auto</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Voucher Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>New Voucher</DialogTitle>
            <DialogDescription>Create a double-entry voucher with balanced debit and credit entries.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Type</Label>
                <Select value={form.voucher_type} onValueChange={v => setForm(p => ({ ...p, voucher_type: v }))}>
                  <SelectTrigger data-testid="voucher-type-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {VOUCHER_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Date</Label>
                <Input type="date" value={form.date} onChange={e => setForm(p => ({ ...p, date: e.target.value }))} data-testid="voucher-date-input" />
              </div>
              <div>
                <Label>Reference</Label>
                <Input value={form.reference} onChange={e => setForm(p => ({ ...p, reference: e.target.value }))} placeholder="Ref #" />
              </div>
            </div>
            <div>
              <Label>Narration</Label>
              <Input value={form.narration} onChange={e => setForm(p => ({ ...p, narration: e.target.value }))} placeholder="Description" data-testid="voucher-narration-input" />
            </div>

            {/* Entries */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>Entries</Label>
                <Button variant="ghost" size="sm" onClick={addEntry} data-testid="add-entry-btn">
                  <Plus size={14} className="mr-1" /> Add Line
                </Button>
              </div>
              <div className="border rounded-lg overflow-hidden" style={{ borderColor: 'var(--app-border)' }}>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ background: 'var(--app-bg)' }}>
                      <th className="text-left px-3 py-2 font-medium text-xs" style={{ color: 'var(--app-text-muted)' }}>Ledger</th>
                      <th className="text-right px-3 py-2 font-medium text-xs w-28" style={{ color: '#5C745A' }}>Debit</th>
                      <th className="text-right px-3 py-2 font-medium text-xs w-28" style={{ color: '#C06B52' }}>Credit</th>
                      <th className="w-8"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.entries.map((entry, idx) => (
                      <tr key={idx} className="border-t" style={{ borderColor: 'var(--app-border)' }}>
                        <td className="px-2 py-1.5">
                          <Select value={entry.ledger_id} onValueChange={v => updateEntry(idx, 'ledger_id', v)}>
                            <SelectTrigger className="h-8 text-xs" data-testid={`entry-ledger-${idx}`}><SelectValue placeholder="Select ledger" /></SelectTrigger>
                            <SelectContent>
                              {ledgers.map(l => <SelectItem key={l.id} value={l.id}>{l.name}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        </td>
                        <td className="px-2 py-1.5">
                          <Input type="number" className="h-8 text-xs text-right" value={entry.debit || ''} onChange={e => updateEntry(idx, 'debit', e.target.value)} data-testid={`entry-debit-${idx}`} />
                        </td>
                        <td className="px-2 py-1.5">
                          <Input type="number" className="h-8 text-xs text-right" value={entry.credit || ''} onChange={e => updateEntry(idx, 'credit', e.target.value)} data-testid={`entry-credit-${idx}`} />
                        </td>
                        <td className="px-1">
                          {form.entries.length > 2 && (
                            <button onClick={() => removeEntry(idx)} className="p-1 rounded hover:bg-black/5">
                              <Trash size={12} style={{ color: '#C06B52' }} />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--app-text-muted)' }}>
                      <td className="px-3 py-2 text-xs" style={{ color: 'var(--app-text)' }}>Total</td>
                      <td className="px-3 py-2 text-right text-xs font-mono" style={{ color: '#5C745A' }}>{totalDebit.toLocaleString('en-IN')}</td>
                      <td className="px-3 py-2 text-right text-xs font-mono" style={{ color: '#C06B52' }}>{totalCredit.toLocaleString('en-IN')}</td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
              {!isBalanced && totalDebit > 0 && (
                <p className="text-xs mt-1.5 font-medium" style={{ color: '#C06B52' }}>
                  Difference: {Math.abs(totalDebit - totalCredit).toLocaleString('en-IN')} ({totalDebit > totalCredit ? 'Dr excess' : 'Cr excess'})
                </p>
              )}
            </div>

            <Button onClick={createVoucher} className="w-full" disabled={!isBalanced || totalDebit === 0} data-testid="submit-voucher-btn">
              Create Voucher
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Vouchers;
