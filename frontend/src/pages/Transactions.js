import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Plus, Trash, Pencil, Repeat, Sparkle, FunnelSimple, X } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Transactions = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [open, setOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [categorizing, setCategorizing] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [formData, setFormData] = useState({
    account_id: '', date: new Date().toISOString().split('T')[0],
    description: '', amount: 0, transaction_type: 'debit', category_id: '', notes: ''
  });
  const [transferData, setTransferData] = useState({
    from_account_id: '', to_account_id: '', amount: 0,
    date: new Date().toISOString().split('T')[0], description: 'Transfer'
  });
  const [potentialTransfers, setPotentialTransfers] = useState([]);

  // Filters — initialized from URL params
  const [filterType, setFilterType] = useState(searchParams.get('type') || 'all');
  const [filterAccount, setFilterAccount] = useState(searchParams.get('account') || 'all');
  const [filterCategory, setFilterCategory] = useState(searchParams.get('category') || 'all');
  const [filterDateFrom, setFilterDateFrom] = useState(searchParams.get('dateFrom') || '');
  const [filterDateTo, setFilterDateTo] = useState(searchParams.get('dateTo') || '');
  const [filterSearch, setFilterSearch] = useState(searchParams.get('search') || '');
  const [showFilters, setShowFilters] = useState(() => {
    return !!(searchParams.get('account') || searchParams.get('category') || searchParams.get('dateFrom') || searchParams.get('dateTo'));
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [txnRes, accRes, catRes] = await Promise.all([
        axios.get(`${API}/transactions`),
        axios.get(`${API}/accounts`),
        axios.get(`${API}/categories`)
      ]);
      setTransactions(txnRes.data);
      setAccounts(accRes.data);
      setCategories(catRes.data);
    } catch { toast.error('Failed to load data'); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTransaction) {
        await axios.put(`${API}/transactions/${editingTransaction.id}`, formData);
        toast.success('Transaction updated');
      } else {
        await axios.post(`${API}/transactions`, formData);
        toast.success('Transaction added');
      }
      setOpen(false);
      setEditingTransaction(null);
      setFormData({ account_id: '', date: new Date().toISOString().split('T')[0], description: '', amount: 0, transaction_type: 'debit', category_id: '', notes: '' });
      loadData();
    } catch { toast.error('Failed to save transaction'); }
  };

  const handleTransferSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/transfers`, transferData);
      toast.success('Transfer created');
      setTransferOpen(false);
      setTransferData({ from_account_id: '', to_account_id: '', amount: 0, date: new Date().toISOString().split('T')[0], description: 'Transfer' });
      loadData();
    } catch { toast.error('Failed to create transfer'); }
  };

  const handleDelete = async (id) => {
    try {
      await axios.delete(`${API}/transactions/${id}`);
      toast.success('Transaction deleted');
      loadData();
    } catch { toast.error('Failed to delete'); }
  };

  const handleEdit = (txn) => {
    setEditingTransaction(txn);
    setFormData({
      account_id: txn.account_id, date: txn.date, description: txn.description,
      amount: txn.amount, transaction_type: txn.transaction_type,
      category_id: txn.category_id || '', notes: txn.notes || ''
    });
    setOpen(true);
  };

  const getAccountName = (id) => accounts.find(a => a.id === id)?.name || 'Unknown';
  const getCategoryName = (id) => {
    if (!id) return null;
    return categories.find(c => c.id === id)?.name || null;
  };
  const getCategoryColor = (id) => {
    if (!id) return null;
    return categories.find(c => c.id === id)?.color || null;
  };

  const uncategorizedCount = transactions.filter(t => !t.category_id || !categories.find(c => c.id === t.category_id)).length;

  const handleAICategorize = async () => {
    setCategorizing(true);
    try {
      // First fix orphaned category references
      await axios.post(`${API}/categories/fix-orphaned`);
      const res = await axios.post(`${API}/ai-categorize`, []);
      toast.success(res.data.message);
      loadData();
    } catch { toast.error('AI categorization failed'); }
    finally { setCategorizing(false); }
  };

  const detectTransfers = async () => {
    try {
      const res = await axios.post(`${API}/detect-transfers`);
      setPotentialTransfers(res.data.potential_transfers || []);
      toast.success(`Found ${res.data.count} potential transfers`);
    } catch { toast.error('Failed to detect transfers'); }
  };

  const markAsTransfer = async (id1, id2) => {
    try {
      await axios.post(`${API}/mark-as-transfer`, [id1, id2]);
      toast.success('Marked as transfer');
      detectTransfers();
      loadData();
    } catch { toast.error('Failed to mark transfer'); }
  };

  // Filtered transactions
  const filtered = useMemo(() => {
    return transactions.filter(txn => {
      if (filterType !== 'all' && txn.transaction_type !== filterType) return false;
      if (filterAccount !== 'all' && txn.account_id !== filterAccount) return false;
      if (filterCategory !== 'all') {
        if (filterCategory === 'uncategorized' && txn.category_id) return false;
        if (filterCategory !== 'uncategorized' && txn.category_id !== filterCategory) return false;
      }
      if (filterDateFrom && txn.date < filterDateFrom) return false;
      if (filterDateTo && txn.date > filterDateTo) return false;
      if (filterSearch && !txn.description.toLowerCase().includes(filterSearch.toLowerCase())) return false;
      return true;
    });
  }, [transactions, filterType, filterAccount, filterCategory, filterDateFrom, filterDateTo, filterSearch]);

  const hasActiveFilters = filterType !== 'all' || filterAccount !== 'all' || filterCategory !== 'all' || filterDateFrom || filterDateTo || filterSearch;

  const clearFilters = () => {
    setFilterType('all'); setFilterAccount('all'); setFilterCategory('all');
    setFilterDateFrom(''); setFilterDateTo(''); setFilterSearch('');
    setSearchParams({});
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ color: 'var(--app-text)' }}>Transactions</h2>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>
            {filtered.length} of {transactions.length} transactions
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button data-testid="ai-categorize-btn" onClick={handleAICategorize} disabled={categorizing}
            className="themed-btn-primary rounded-lg text-sm h-9">
            <Sparkle size={16} className="mr-1.5" />
            {categorizing ? 'Categorizing...' : 'AI Categorize'}
            {!categorizing && uncategorizedCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-white/20 font-bold">{uncategorizedCount}</span>
            )}
          </Button>
          <Button data-testid="detect-transfers-btn" onClick={detectTransfers}
            className="themed-badge text-[#1C1917] hover:bg-[#E5E2DC] border border-[var(--app-card-border)] rounded-lg text-sm h-9">
            <Repeat size={16} className="mr-1.5" /> Detect Transfers
          </Button>
          <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
            <DialogTrigger asChild>
              <Button data-testid="add-transfer-btn" className="bg-[#D4A373] text-white hover:bg-[#C0945E] rounded-lg text-sm h-9">
                <Repeat size={16} className="mr-1.5" /> Transfer
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Create Transfer</DialogTitle></DialogHeader>
              <form onSubmit={handleTransferSubmit} className="space-y-4">
                <div>
                  <Label>From Account</Label>
                  <Select value={transferData.from_account_id} onValueChange={val => setTransferData({...transferData, from_account_id: val})}>
                    <SelectTrigger data-testid="from-account-select"><SelectValue placeholder="Select account" /></SelectTrigger>
                    <SelectContent>{accounts.map(a => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>To Account</Label>
                  <Select value={transferData.to_account_id} onValueChange={val => setTransferData({...transferData, to_account_id: val})}>
                    <SelectTrigger data-testid="to-account-select"><SelectValue placeholder="Select account" /></SelectTrigger>
                    <SelectContent>{accounts.map(a => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Amount (₹)</Label>
                  <Input type="number" step="0.01" data-testid="transfer-amount-input" value={transferData.amount}
                    onChange={e => setTransferData({...transferData, amount: parseFloat(e.target.value) || 0})} required />
                </div>
                <div>
                  <Label>Date</Label>
                  <Input type="date" data-testid="transfer-date-input" value={transferData.date}
                    onChange={e => setTransferData({...transferData, date: e.target.value})} required />
                </div>
                <Button type="submit" data-testid="submit-transfer-btn" className="w-full themed-btn-primary rounded-lg">Create Transfer</Button>
              </form>
            </DialogContent>
          </Dialog>
          <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setEditingTransaction(null); setFormData({ account_id: '', date: new Date().toISOString().split('T')[0], description: '', amount: 0, transaction_type: 'debit', category_id: '', notes: '' }); } }}>
            <DialogTrigger asChild>
              <Button data-testid="add-transaction-btn" className="themed-btn-primary rounded-lg text-sm h-9">
                <Plus size={16} className="mr-1.5" /> Add
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>{editingTransaction ? 'Edit Transaction' : 'Add Transaction'}</DialogTitle></DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label>Account</Label>
                  <Select value={formData.account_id} onValueChange={val => setFormData({...formData, account_id: val})}>
                    <SelectTrigger data-testid="transaction-account-select"><SelectValue placeholder="Select account" /></SelectTrigger>
                    <SelectContent>{accounts.map(a => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Type</Label>
                  <Select value={formData.transaction_type} onValueChange={val => setFormData({...formData, transaction_type: val})}>
                    <SelectTrigger data-testid="transaction-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="credit">Credit (Money In)</SelectItem>
                      <SelectItem value="debit">Debit (Money Out)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Description</Label>
                  <Input data-testid="transaction-description-input" value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})} placeholder="e.g., Grocery shopping" required />
                </div>
                <div>
                  <Label>Amount (₹)</Label>
                  <Input type="number" step="0.01" data-testid="transaction-amount-input" value={formData.amount}
                    onChange={e => setFormData({...formData, amount: parseFloat(e.target.value) || 0})} required />
                </div>
                <div>
                  <Label>Category</Label>
                  <Select value={formData.category_id} onValueChange={val => setFormData({...formData, category_id: val})}>
                    <SelectTrigger data-testid="transaction-category-select"><SelectValue placeholder="Select category" /></SelectTrigger>
                    <SelectContent>
                      {categories.filter(c => c.category_type === (formData.transaction_type === 'credit' ? 'income' : 'expense')).map(cat =>
                        <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Date</Label>
                  <Input type="date" data-testid="transaction-date-input" value={formData.date}
                    onChange={e => setFormData({...formData, date: e.target.value})} required />
                </div>
                <div>
                  <Label>Notes (Optional)</Label>
                  <Input data-testid="transaction-notes-input" value={formData.notes}
                    onChange={e => setFormData({...formData, notes: e.target.value})} placeholder="Additional notes" />
                </div>
                <Button type="submit" data-testid="save-transaction-btn" className="w-full themed-btn-primary rounded-lg">
                  {editingTransaction ? 'Update' : 'Add'} Transaction
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="themed-card rounded-lg p-3 shadow-sm">
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={() => setShowFilters(!showFilters)} data-testid="toggle-filters-btn"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            style={{ background: hasActiveFilters ? 'var(--app-accent-light)' : 'transparent',
              color: hasActiveFilters ? 'var(--app-accent)' : 'var(--app-text-secondary)',
              border: '1px solid var(--app-card-border)' }}>
            <FunnelSimple size={16} /> Filters {hasActiveFilters && `(active)`}
          </button>
          {/* Quick type pills */}
          {['all', 'credit', 'debit'].map(t => (
            <button key={t} onClick={() => setFilterType(t)} data-testid={`filter-type-${t}`}
              className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
              style={{
                background: filterType === t ? (t === 'credit' ? '#5C745A' : t === 'debit' ? '#C06B52' : 'var(--app-accent)') : 'transparent',
                color: filterType === t ? '#fff' : 'var(--app-text-secondary)',
                border: filterType === t ? 'none' : '1px solid var(--app-card-border)'
              }}>
              {t === 'all' ? 'All' : t === 'credit' ? 'Credit' : 'Debit'}
            </button>
          ))}
          {/* Search */}
          <div className="flex-1 min-w-[140px]">
            <Input placeholder="Search description..." value={filterSearch}
              data-testid="filter-search-input"
              onChange={e => setFilterSearch(e.target.value)}
              className="h-8 text-sm" />
          </div>
          {hasActiveFilters && (
            <button onClick={clearFilters} data-testid="clear-filters-btn"
              className="flex items-center gap-1 text-xs px-2 py-1 rounded"
              style={{ color: 'var(--app-danger)' }}>
              <X size={14} /> Clear
            </button>
          )}
        </div>
        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 pt-3 border-t" style={{ borderColor: 'var(--app-card-border)' }}>
            <div>
              <Label className="text-xs">Account</Label>
              <Select value={filterAccount} onValueChange={setFilterAccount}>
                <SelectTrigger data-testid="filter-account-select" className="h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Accounts</SelectItem>
                  {accounts.map(a => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Category</Label>
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger data-testid="filter-category-select" className="h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="uncategorized">Uncategorized</SelectItem>
                  {categories.map(c => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">From Date</Label>
              <Input type="date" value={filterDateFrom} onChange={e => setFilterDateFrom(e.target.value)}
                data-testid="filter-date-from" className="h-8 text-sm" />
            </div>
            <div>
              <Label className="text-xs">To Date</Label>
              <Input type="date" value={filterDateTo} onChange={e => setFilterDateTo(e.target.value)}
                data-testid="filter-date-to" className="h-8 text-sm" />
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList>
          <TabsTrigger value="all" data-testid="all-transactions-tab">Transactions</TabsTrigger>
          <TabsTrigger value="transfers" data-testid="potential-transfers-tab">
            Potential Transfers ({potentialTransfers.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all">
          <div className="themed-card rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="themed-badge border-b border-[var(--app-card-border)]">
                  <tr>
                    <th className="text-left p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Date</th>
                    <th className="text-left p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Account</th>
                    <th className="text-left p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Description</th>
                    <th className="text-left p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Category</th>
                    <th className="text-right p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Amount</th>
                    <th className="text-right p-3 text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-secondary)' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(txn => (
                    <tr key={txn.id} className="border-b border-[var(--app-card-border)] hover:themed-badge transition-colors duration-150">
                      <td className="p-3 text-sm" style={{ color: 'var(--app-text)' }}>{txn.date}</td>
                      <td className="p-3 text-sm" style={{ color: 'var(--app-text)' }}>{getAccountName(txn.account_id)}</td>
                      <td className="p-3 text-sm max-w-[260px] truncate" style={{ color: 'var(--app-text)' }}>
                        {txn.description}
                        {txn.is_transfer && <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-[#78716C] text-white rounded">Transfer</span>}
                      </td>
                      <td className="p-3 text-sm" style={{ color: 'var(--app-text-secondary)' }}>
                        {getCategoryName(txn.category_id) ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                            style={{ background: getCategoryColor(txn.category_id) ? `${getCategoryColor(txn.category_id)}15` : 'var(--app-accent-light)', color: getCategoryColor(txn.category_id) || 'var(--app-accent-text)' }}>
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: getCategoryColor(txn.category_id) || 'var(--app-accent)' }} />
                            {getCategoryName(txn.category_id)}
                          </span>
                        ) : (
                          <span className="text-xs italic" style={{ color: 'var(--app-text-muted)' }}>Uncategorized</span>
                        )}
                      </td>
                      <td className="p-3 text-sm text-right font-medium" style={{ color: txn.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                        {txn.transaction_type === 'credit' ? '+' : '-'}₹{txn.amount.toFixed(2)}
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => handleEdit(txn)} data-testid={`edit-transaction-${txn.id}`}
                            className="text-[#5C745A] hover:text-[#475F45] transition-colors"><Pencil size={15} /></button>
                          <button onClick={() => handleDelete(txn.id)} data-testid={`delete-transaction-${txn.id}`}
                            className="text-[#C06B52] hover:text-[#A35943] transition-colors"><Trash size={15} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filtered.length === 0 && (
              <div className="p-12 text-center" style={{ color: 'var(--app-text-muted)' }}>
                {hasActiveFilters ? 'No transactions match the current filters.' : 'No transactions yet. Add your first transaction!'}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="transfers">
          <div className="space-y-4">
            {potentialTransfers.map((transfer, idx) => (
              <div key={idx} className="themed-card rounded-lg p-5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1 grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.15em] mb-1" style={{ color: 'var(--app-text-secondary)' }}>Transaction 1</div>
                      <div className="text-sm" style={{ color: 'var(--app-text)' }}>{getAccountName(transfer.txn1.account_id)} - {transfer.txn1.description}</div>
                      <div className="text-sm" style={{ color: transfer.txn1.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                        {transfer.txn1.transaction_type === 'credit' ? '+' : '-'}₹{transfer.txn1.amount.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-[0.15em] mb-1" style={{ color: 'var(--app-text-secondary)' }}>Transaction 2</div>
                      <div className="text-sm" style={{ color: 'var(--app-text)' }}>{getAccountName(transfer.txn2.account_id)} - {transfer.txn2.description}</div>
                      <div className="text-sm" style={{ color: transfer.txn2.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                        {transfer.txn2.transaction_type === 'credit' ? '+' : '-'}₹{transfer.txn2.amount.toFixed(2)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs mb-1.5 flex items-center gap-2 justify-end" style={{ color: 'var(--app-text-secondary)' }}>
                      {transfer.date}
                      {transfer.confidence && (
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          transfer.confidence === 'high' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                        }`} data-testid={`transfer-confidence-${idx}`}>{transfer.confidence}</span>
                      )}
                    </div>
                    <Button onClick={() => markAsTransfer(transfer.txn1.id, transfer.txn2.id)}
                      data-testid={`mark-transfer-${idx}`} className="themed-btn-primary rounded-lg text-sm">
                      Mark as Transfer
                    </Button>
                  </div>
                </div>
              </div>
            ))}
            {potentialTransfers.length === 0 && (
              <div className="themed-card rounded-lg p-12 text-center" style={{ color: 'var(--app-text-muted)' }}>
                No potential transfers detected. Click "Detect Transfers" to scan.
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Transactions;
