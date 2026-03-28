import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Plus, Trash, Pencil, Repeat } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Transactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [open, setOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [formData, setFormData] = useState({
    account_id: '',
    date: new Date().toISOString().split('T')[0],
    description: '',
    amount: 0,
    transaction_type: 'debit',
    category_id: '',
    notes: ''
  });
  const [transferData, setTransferData] = useState({
    from_account_id: '',
    to_account_id: '',
    amount: 0,
    date: new Date().toISOString().split('T')[0],
    description: 'Transfer'
  });
  const [potentialTransfers, setPotentialTransfers] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

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
    } catch (err) {
      toast.error('Failed to load data');
      console.error(err);
    }
  };

  const detectTransfers = async () => {
    try {
      const res = await axios.post(`${API}/detect-transfers`);
      setPotentialTransfers(res.data.potential_transfers);
      if (res.data.count > 0) {
        toast.success(`Found ${res.data.count} potential transfers`);
      } else {
        toast.info('No potential transfers detected');
      }
    } catch (err) {
      toast.error('Failed to detect transfers');
      console.error(err);
    }
  };

  const markAsTransfer = async (txn1Id, txn2Id) => {
    try {
      await axios.post(`${API}/mark-as-transfer`, [txn1Id, txn2Id]);
      toast.success('Marked as transfer');
      loadData();
      detectTransfers();
    } catch (err) {
      toast.error('Failed to mark as transfer');
      console.error(err);
    }
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
      setFormData({
        account_id: '',
        date: new Date().toISOString().split('T')[0],
        description: '',
        amount: 0,
        transaction_type: 'debit',
        category_id: '',
        notes: ''
      });
      loadData();
    } catch (err) {
      toast.error('Failed to save transaction');
      console.error(err);
    }
  };

  const handleTransferSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/transfers`, transferData);
      toast.success('Transfer created');
      setTransferOpen(false);
      setTransferData({
        from_account_id: '',
        to_account_id: '',
        amount: 0,
        date: new Date().toISOString().split('T')[0],
        description: 'Transfer'
      });
      loadData();
    } catch (err) {
      toast.error('Failed to create transfer');
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this transaction?')) return;
    try {
      await axios.delete(`${API}/transactions/${id}`);
      toast.success('Transaction deleted');
      loadData();
    } catch (err) {
      toast.error('Failed to delete transaction');
      console.error(err);
    }
  };

  const handleEdit = (txn) => {
    setEditingTransaction(txn);
    setFormData({
      account_id: txn.account_id,
      date: txn.date,
      description: txn.description,
      amount: txn.amount,
      transaction_type: txn.transaction_type,
      category_id: txn.category_id || '',
      notes: txn.notes || ''
    });
    setOpen(true);
  };

  const getAccountName = (id) => accounts.find(a => a.id === id)?.name || 'Unknown';
  const getCategoryName = (id) => categories.find(c => c.id === id)?.name || 'Uncategorized';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
            Transactions
          </h2>
          <p className="text-sm mt-1" style={{ color: '#78716C' }}>Track all your financial transactions</p>
        </div>
        <div className="flex gap-2">
          <Button
            data-testid="detect-transfers-btn"
            onClick={detectTransfers}
            className="bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
          >
            <Repeat size={18} className="mr-2" />
            Detect Transfers
          </Button>
          <Dialog open={transferOpen} onOpenChange={setTransferOpen}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-transfer-btn"
                className="bg-[#D4A373] text-white hover:bg-[#C0945E] rounded-lg"
              >
                <Repeat size={18} className="mr-2" />
                Add Transfer
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Transfer</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleTransferSubmit} className="space-y-4">
                <div>
                  <Label>From Account</Label>
                  <Select value={transferData.from_account_id} onValueChange={val => setTransferData({...transferData, from_account_id: val})}>
                    <SelectTrigger data-testid="from-account-select">
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(acc => (
                        <SelectItem key={acc.id} value={acc.id}>{acc.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>To Account</Label>
                  <Select value={transferData.to_account_id} onValueChange={val => setTransferData({...transferData, to_account_id: val})}>
                    <SelectTrigger data-testid="to-account-select">
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(acc => (
                        <SelectItem key={acc.id} value={acc.id}>{acc.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="transfer-amount-input"
                    value={transferData.amount}
                    onChange={e => setTransferData({...transferData, amount: parseFloat(e.target.value) || 0})}
                    required
                  />
                </div>
                <div>
                  <Label>Date</Label>
                  <Input
                    type="date"
                    data-testid="transfer-date-input"
                    value={transferData.date}
                    onChange={e => setTransferData({...transferData, date: e.target.value})}
                    required
                  />
                </div>
                <Button type="submit" data-testid="save-transfer-btn" className="w-full bg-[#D4A373] text-white hover:bg-[#C0945E] rounded-lg">
                  Create Transfer
                </Button>
              </form>
            </DialogContent>
          </Dialog>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-transaction-btn"
                className="bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
                onClick={() => {
                  setEditingTransaction(null);
                  setFormData({
                    account_id: '',
                    date: new Date().toISOString().split('T')[0],
                    description: '',
                    amount: 0,
                    transaction_type: 'debit',
                    category_id: '',
                    notes: ''
                  });
                }}
              >
                <Plus size={18} className="mr-2" />
                Add Transaction
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{editingTransaction ? 'Edit Transaction' : 'Add Transaction'}</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label>Account</Label>
                  <Select value={formData.account_id} onValueChange={val => setFormData({...formData, account_id: val})}>
                    <SelectTrigger data-testid="transaction-account-select">
                      <SelectValue placeholder="Select account" />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts.map(acc => (
                        <SelectItem key={acc.id} value={acc.id}>{acc.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Type</Label>
                  <Select value={formData.transaction_type} onValueChange={val => setFormData({...formData, transaction_type: val})}>
                    <SelectTrigger data-testid="transaction-type-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="credit">Credit (Money In)</SelectItem>
                      <SelectItem value="debit">Debit (Money Out)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Description</Label>
                  <Input
                    data-testid="transaction-description-input"
                    value={formData.description}
                    onChange={e => setFormData({...formData, description: e.target.value})}
                    placeholder="e.g., Grocery shopping"
                    required
                  />
                </div>
                <div>
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    data-testid="transaction-amount-input"
                    value={formData.amount}
                    onChange={e => setFormData({...formData, amount: parseFloat(e.target.value) || 0})}
                    required
                  />
                </div>
                <div>
                  <Label>Category</Label>
                  <Select value={formData.category_id} onValueChange={val => setFormData({...formData, category_id: val})}>
                    <SelectTrigger data-testid="transaction-category-select">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.filter(c => c.category_type === (formData.transaction_type === 'credit' ? 'income' : 'expense')).map(cat => (
                        <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Date</Label>
                  <Input
                    type="date"
                    data-testid="transaction-date-input"
                    value={formData.date}
                    onChange={e => setFormData({...formData, date: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label>Notes (Optional)</Label>
                  <Input
                    data-testid="transaction-notes-input"
                    value={formData.notes}
                    onChange={e => setFormData({...formData, notes: e.target.value})}
                    placeholder="Additional notes"
                  />
                </div>
                <Button type="submit" data-testid="save-transaction-btn" className="w-full bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg">
                  {editingTransaction ? 'Update' : 'Add'} Transaction
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Tabs for Transactions and Potential Transfers */}
      <Tabs defaultValue="all" className="w-full">
        <TabsList>
          <TabsTrigger value="all" data-testid="all-transactions-tab">All Transactions</TabsTrigger>
          <TabsTrigger value="transfers" data-testid="potential-transfers-tab">
            Potential Transfers ({potentialTransfers.length})
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="all">
          <div className="bg-white border border-[#E5E2DC] rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[#F9F8F6] border-b border-[#E5E2DC]">
                  <tr>
                    <th className="text-left p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Date</th>
                    <th className="text-left p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Account</th>
                    <th className="text-left p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Description</th>
                    <th className="text-left p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Category</th>
                    <th className="text-right p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Amount</th>
                    <th className="text-right p-4 text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(txn => (
                    <tr key={txn.id} className="border-b border-[#E5E2DC] hover:bg-[#F9F8F6] transition-colors duration-200">
                      <td className="p-4 text-sm" style={{ color: '#1C1917' }}>{txn.date}</td>
                      <td className="p-4 text-sm" style={{ color: '#1C1917' }}>{getAccountName(txn.account_id)}</td>
                      <td className="p-4 text-sm" style={{ color: '#1C1917' }}>
                        {txn.description}
                        {txn.is_transfer && <span className="ml-2 text-xs px-2 py-0.5 bg-[#78716C] text-white rounded">Transfer</span>}
                      </td>
                      <td className="p-4 text-sm" style={{ color: '#78716C' }}>{getCategoryName(txn.category_id)}</td>
                      <td className="p-4 text-sm text-right font-medium" style={{ color: txn.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                        {txn.transaction_type === 'credit' ? '+' : '-'}₹{txn.amount.toFixed(2)}
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleEdit(txn)}
                            data-testid={`edit-transaction-${txn.id}`}
                            className="text-[#5C745A] hover:text-[#475F45] transition-colors duration-200"
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            onClick={() => handleDelete(txn.id)}
                            data-testid={`delete-transaction-${txn.id}`}
                            className="text-[#C06B52] hover:text-[#A35943] transition-colors duration-200"
                          >
                            <Trash size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {transactions.length === 0 && (
              <div className="p-12 text-center" style={{ color: '#A8A29E' }}>
                No transactions yet. Add your first transaction!
              </div>
            )}
          </div>
        </TabsContent>
        
        <TabsContent value="transfers">
          <div className="space-y-4">
            {potentialTransfers.map((transfer, idx) => (
              <div key={idx} className="bg-white border border-[#E5E2DC] rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <div className="text-xs uppercase tracking-[0.2em] mb-1" style={{ color: '#78716C' }}>Transaction 1</div>
                        <div className="text-sm" style={{ color: '#1C1917' }}>
                          {getAccountName(transfer.txn1.account_id)} - {transfer.txn1.description}
                        </div>
                        <div className="text-sm" style={{ color: transfer.txn1.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                          {transfer.txn1.transaction_type === 'credit' ? '+' : '-'}₹{transfer.txn1.amount.toFixed(2)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs uppercase tracking-[0.2em] mb-1" style={{ color: '#78716C' }}>Transaction 2</div>
                        <div className="text-sm" style={{ color: '#1C1917' }}>
                          {getAccountName(transfer.txn2.account_id)} - {transfer.txn2.description}
                        </div>
                        <div className="text-sm" style={{ color: transfer.txn2.transaction_type === 'credit' ? '#5C745A' : '#C06B52' }}>
                          {transfer.txn2.transaction_type === 'credit' ? '+' : '-'}₹{transfer.txn2.amount.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <div className="text-xs mt-2" style={{ color: '#78716C' }}>Date: {transfer.date}</div>
                  </div>
                  <Button
                    onClick={() => markAsTransfer(transfer.txn1.id, transfer.txn2.id)}
                    data-testid={`mark-transfer-${idx}`}
                    className="bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
                  >
                    Mark as Transfer
                  </Button>
                </div>
              </div>
            ))}
            {potentialTransfers.length === 0 && (
              <div className="bg-white border border-[#E5E2DC] rounded-lg p-12 text-center" style={{ color: '#A8A29E' }}>
                No potential transfers detected. Click "Detect Transfers" to scan for matching transactions.
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Transactions;
