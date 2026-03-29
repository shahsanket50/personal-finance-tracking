import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Trash, Pencil, Sparkle } from '@phosphor-icons/react';
import ParserBuilder from './ParserBuilder';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Accounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [open, setOpen] = useState(false);
  const [parserBuilderOpen, setParserBuilderOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [editingAccount, setEditingAccount] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    account_type: 'bank',
    start_balance: 0,
    email_filter: ''
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const res = await axios.get(`${API}/accounts`);
      setAccounts(res.data);
    } catch (err) {
      toast.error('Failed to load accounts');
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingAccount) {
        await axios.put(`${API}/accounts/${editingAccount.id}`, formData);
        toast.success('Account updated');
      } else {
        await axios.post(`${API}/accounts`, formData);
        toast.success('Account created');
      }
      setOpen(false);
      setEditingAccount(null);
      setFormData({ name: '', account_type: 'bank', start_balance: 0, email_filter: '' });
      loadAccounts();
    } catch (err) {
      toast.error('Failed to save account');
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this account?')) return;
    try {
      await axios.delete(`${API}/accounts/${id}`);
      toast.success('Account deleted');
      loadAccounts();
    } catch (err) {
      toast.error('Failed to delete account');
      console.error(err);
    }
  };

  const handleEdit = (account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      account_type: account.account_type,
      start_balance: account.start_balance,
      email_filter: account.email_filter || ''
    });
    setOpen(true);
  };

  const openParserBuilder = (account) => {
    setSelectedAccount(account);
    setParserBuilderOpen(true);
  };

  const handleParserSaved = () => {
    loadAccounts();
    toast.success('Parser configured successfully!');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
            Accounts
          </h2>
          <p className="text-sm mt-1" style={{ color: '#78716C' }}>Manage your financial accounts</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button 
              data-testid="add-account-btn"
              className="bg-[#5C745A] text-white hover:bg-[#475F45] focus:ring-2 focus:ring-[#5C745A]/50 rounded-lg"
              onClick={() => {
                setEditingAccount(null);
                setFormData({ name: '', account_type: 'bank', start_balance: 0, email_filter: '' });
              }}
            >
              <Plus size={18} className="mr-2" />
              Add Account
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingAccount ? 'Edit Account' : 'Add New Account'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">Account Name</Label>
                <Input
                  id="name"
                  data-testid="account-name-input"
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g., HDFC Savings"
                  required
                />
              </div>
              <div>
                <Label htmlFor="type">Account Type</Label>
                <Select 
                  value={formData.account_type} 
                  onValueChange={val => setFormData({...formData, account_type: val})}
                >
                  <SelectTrigger data-testid="account-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank">Bank Account</SelectItem>
                    <SelectItem value="credit_card">Credit Card</SelectItem>
                    <SelectItem value="investment">Investment</SelectItem>
                    <SelectItem value="cash">Cash</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="balance">Starting Balance (₹)</Label>
                <Input
                  id="balance"
                  type="number"
                  step="0.01"
                  data-testid="account-balance-input"
                  value={formData.start_balance}
                  onChange={e => setFormData({...formData, start_balance: parseFloat(e.target.value) || 0})}
                  required
                />
              </div>
              <div>
                <Label htmlFor="email_filter">Email Filter (for auto-scan)</Label>
                <Input
                  id="email_filter"
                  data-testid="account-email-filter-input"
                  value={formData.email_filter}
                  onChange={e => setFormData({...formData, email_filter: e.target.value})}
                  placeholder="e.g., HDFC Bank Statement"
                />
                <p className="text-xs mt-1" style={{ color: '#A8A29E' }}>Keyword to match in email subject for auto-importing statements</p>
              </div>
              <Button 
                type="submit" 
                data-testid="save-account-btn"
                className="w-full bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
              >
                {editingAccount ? 'Update' : 'Create'} Account
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Accounts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {accounts.map(account => (
          <div 
            key={account.id}
            data-testid={`account-card-${account.id}`}
            className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="text-xs uppercase tracking-[0.2em]" style={{ color: '#78716C' }}>
                {account.account_type.replace('_', ' ')}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openParserBuilder(account)}
                  data-testid={`build-parser-${account.id}`}
                  className="text-[#7CA1A6] hover:text-[#5C745A] transition-colors duration-200"
                  title="Build PDF Parser"
                >
                  <Sparkle size={18} weight="fill" />
                </button>
                <button
                  onClick={() => handleEdit(account)}
                  data-testid={`edit-account-${account.id}`}
                  className="text-[#5C745A] hover:text-[#475F45] transition-colors duration-200"
                >
                  <Pencil size={18} />
                </button>
                <button
                  onClick={() => handleDelete(account.id)}
                  data-testid={`delete-account-${account.id}`}
                  className="text-[#C06B52] hover:text-[#A35943] transition-colors duration-200"
                >
                  <Trash size={18} />
                </button>
              </div>
            </div>
            <h3 className="font-heading text-xl mb-2" style={{ color: '#1C1917' }}>
              {account.name}
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-xs" style={{ color: '#78716C' }}>Current Balance</span>
                <div className="font-heading text-2xl" style={{ color: '#5C745A' }}>
                  ₹{account.current_balance.toFixed(2)}
                </div>
              </div>
              <div>
                <span className="text-xs" style={{ color: '#78716C' }}>Starting Balance</span>
                <div className="text-sm" style={{ color: '#1C1917' }}>
                  ₹{account.start_balance.toFixed(2)}
                </div>
              </div>
              {account.custom_parser && (
                <div className="mt-3 px-2 py-1 bg-[#E7F3F0] border border-[#5C745A] rounded text-xs flex items-center gap-1" style={{ color: '#2D4A39' }}>
                  <Sparkle size={14} weight="fill" />
                  Custom parser configured
                </div>
              )}
              {account.email_filter && (
                <div className="mt-2 px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs" style={{ color: '#1e40af' }}>
                  Email filter: {account.email_filter}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Parser Builder Modal */}
      {selectedAccount && (
        <ParserBuilder
          account={selectedAccount}
          open={parserBuilderOpen}
          onClose={() => {
            setParserBuilderOpen(false);
            setSelectedAccount(null);
          }}
          onSave={handleParserSaved}
        />
      )}

      {accounts.length === 0 && (
        <div className="bg-white border border-[#E5E2DC] rounded-lg p-12 text-center">
          <p className="text-lg mb-2" style={{ color: '#78716C' }}>No accounts yet</p>
          <p className="text-sm" style={{ color: '#A8A29E' }}>Create your first account to start tracking your finances</p>
        </div>
      )}
    </div>
  );
};

export default Accounts;
