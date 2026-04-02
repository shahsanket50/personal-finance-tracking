import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Trash, Pencil, Sparkle, ArrowClockwise, ClockCounterClockwise, Eye } from '@phosphor-icons/react';
import ParserBuilder from './ParserBuilder';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Accounts = () => {
  const [accounts, setAccounts] = useState([]);
  const [open, setOpen] = useState(false);
  const [parserBuilderOpen, setParserBuilderOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [editingAccount, setEditingAccount] = useState(null);
  const [syncingId, setSyncingId] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyAccount, setHistoryAccount] = useState(null);
  const [syncHistory, setSyncHistory] = useState([]);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [previewingId, setPreviewingId] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    account_type: 'bank',
    start_balance: 0,
    email_filter: '',
    email_from_filter: '',
    pdf_password: ''
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
      setFormData({ name: '', account_type: 'bank', start_balance: 0, email_filter: '', email_from_filter: '', pdf_password: '' });
      loadAccounts();
    } catch (err) {
      toast.error('Failed to save account');
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await axios.delete(`${API}/accounts/${id}`);
      toast.success(res.data.message || 'Account deleted');
      setDeleteTarget(null);
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
      email_filter: account.email_filter || '',
      email_from_filter: account.email_from_filter || '',
      pdf_password: account.pdf_password || ''
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

  const handleSync = async (account) => {
    setSyncingId(account.id);
    try {
      const res = await axios.post(`${API}/accounts/${account.id}/sync`);
      const status = res.data.status || '';
      if (['password_error', 'parse_error'].includes(status)) {
        toast.error(res.data.message);
      } else if (['no_match', 'no_pdfs', 'no_transactions'].includes(status)) {
        toast.warning(res.data.message);
      } else if (res.data.total_imported > 0) {
        toast.success(res.data.message);
      } else {
        toast.info(res.data.message);
      }
      loadAccounts();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Sync failed';
      toast.error(detail);
    } finally {
      setSyncingId(null);
    }
  };

  const openSyncHistory = async (account) => {
    setHistoryAccount(account);
    setHistoryOpen(true);
    try {
      const res = await axios.get(`${API}/accounts/${account.id}/sync-history`);
      setSyncHistory(res.data);
    } catch {
      toast.error('Failed to load sync history');
      setSyncHistory([]);
    }
  };

  const handlePreview = async (account) => {
    setPreviewingId(account.id);
    try {
      const res = await axios.post(`${API}/accounts/${account.id}/sync-preview`);
      setPreviewData(res.data);
      setPreviewOpen(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Preview failed');
    } finally {
      setPreviewingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--app-text)' }}>
            Accounts
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Manage your financial accounts</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button 
              data-testid="add-account-btn"
              className="themed-btn-primary focus:ring-2 focus:ring-[#5C745A]/50 rounded-lg"
              onClick={() => {
                setEditingAccount(null);
                setFormData({ name: '', account_type: 'bank', start_balance: 0, email_filter: '', email_from_filter: '', pdf_password: '' });
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
                <Label htmlFor="email_filter">Email Subject Filter</Label>
                <Input
                  id="email_filter"
                  data-testid="account-email-filter-input"
                  value={formData.email_filter}
                  onChange={e => setFormData({...formData, email_filter: e.target.value})}
                  placeholder="e.g., HDFC Bank Statement"
                />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Keyword to match in email subject</p>
              </div>
              <div>
                <Label htmlFor="email_from_filter">From Email Filter (optional)</Label>
                <Input
                  id="email_from_filter"
                  data-testid="account-email-from-filter-input"
                  value={formData.email_from_filter}
                  onChange={e => setFormData({...formData, email_from_filter: e.target.value})}
                  placeholder="e.g., alerts@hdfcbank.net"
                />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Only match emails from this sender address</p>
              </div>
              <div>
                <Label htmlFor="pdf_password">PDF Password (for encrypted statements)</Label>
                <Input
                  id="pdf_password"
                  type="password"
                  data-testid="account-pdf-password-input"
                  value={formData.pdf_password}
                  onChange={e => setFormData({...formData, pdf_password: e.target.value})}
                  placeholder="Leave blank if not password-protected"
                />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Password to open encrypted PDF statements (e.g., DOB or PAN for HDFC)</p>
              </div>
              <Button 
                type="submit" 
                data-testid="save-account-btn"
                className="w-full themed-btn-primary rounded-lg"
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
            className="themed-card rounded-lg p-6 shadow-sm hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="text-xs uppercase tracking-[0.2em]" style={{ color: 'var(--app-text-secondary)' }}>
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
                  onClick={() => setDeleteTarget(account)}
                  data-testid={`delete-account-${account.id}`}
                  className="text-[#C06B52] hover:text-[#A35943] transition-colors duration-200"
                >
                  <Trash size={18} />
                </button>
              </div>
            </div>
            <h3 className="font-heading text-xl mb-2" style={{ color: 'var(--app-text)' }}>
              {account.name}
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-xs" style={{ color: 'var(--app-text-secondary)' }}>Current Balance</span>
                <div className="font-heading text-2xl" style={{ color: 'var(--app-accent)' }}>
                  ₹{account.current_balance.toFixed(2)}
                </div>
              </div>
              <div>
                <span className="text-xs" style={{ color: 'var(--app-text-secondary)' }}>Starting Balance</span>
                <div className="text-sm" style={{ color: 'var(--app-text)' }}>
                  ₹{account.start_balance.toFixed(2)}
                </div>
              </div>
              {account.custom_parser && (
                <div className="mt-3 px-2 py-1 bg-[var(--app-accent-light)] border border-[var(--app-accent)] rounded text-xs flex items-center gap-1" style={{ color: 'var(--app-accent-text)' }}>
                  <Sparkle size={14} weight="fill" />
                  Custom parser configured
                </div>
              )}
              {account.pdf_password && (
                <div className="mt-2 px-2 py-1 rounded text-xs flex items-center gap-1" style={{ background: 'var(--app-badge-bg)', color: 'var(--app-text-secondary)' }}>
                  PDF password set
                </div>
              )}
              {account.email_filter && (
                <div className="mt-2 px-2 py-1 bg-blue-50 border border-blue-200 rounded text-xs" style={{ color: '#1e40af' }}>
                  Subject: {account.email_filter}
                  {account.email_from_filter && <span className="ml-1 opacity-70">| From: {account.email_from_filter}</span>}
                </div>
              )}
              {account.email_filter && (
                <div className="mt-3 flex gap-2 flex-wrap">
                  <Button
                    size="sm"
                    data-testid={`preview-account-${account.id}`}
                    disabled={previewingId === account.id}
                    onClick={() => handlePreview(account)}
                    className="rounded-lg text-xs h-8 px-3 border"
                    style={{ borderColor: 'var(--app-accent)', color: 'var(--app-accent)', background: 'transparent' }}
                  >
                    <Eye size={14} className={`mr-1.5 ${previewingId === account.id ? 'animate-pulse' : ''}`} />
                    {previewingId === account.id ? 'Loading...' : 'Preview'}
                  </Button>
                  <Button
                    size="sm"
                    data-testid={`sync-account-${account.id}`}
                    disabled={syncingId === account.id}
                    onClick={() => handleSync(account)}
                    className="themed-btn-primary rounded-lg text-xs h-8 px-3"
                  >
                    <ArrowClockwise size={14} className={`mr-1.5 ${syncingId === account.id ? 'animate-spin' : ''}`} />
                    {syncingId === account.id ? 'Syncing...' : 'Sync'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid={`sync-history-${account.id}`}
                    onClick={() => openSyncHistory(account)}
                    className="rounded-lg text-xs h-8 px-3 border"
                    style={{ borderColor: 'var(--app-card-border)', color: 'var(--app-text-secondary)' }}
                  >
                    <ClockCounterClockwise size={14} className="mr-1.5" />
                    History
                  </Button>
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
        <div className="themed-card rounded-lg p-12 text-center">
          <p className="text-lg mb-2" style={{ color: 'var(--app-text-secondary)' }}>No accounts yet</p>
          <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>Create your first account to start tracking your finances</p>
        </div>
      )}

      {/* Sync History Dialog */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ color: 'var(--app-text)' }}>
              Sync History — {historyAccount?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-[400px] overflow-y-auto space-y-3">
            {syncHistory.length === 0 ? (
              <p className="text-sm py-6 text-center" style={{ color: 'var(--app-text-muted)' }}>
                No sync history yet. Click "Sync Email" on the account card to start.
              </p>
            ) : (
              syncHistory.map((log, i) => {
                const statusConfig = {
                  success: { label: 'IMPORTED', color: 'text-green-600' },
                  up_to_date: { label: 'UP TO DATE', color: 'text-blue-500' },
                  all_duplicates: { label: 'NO NEW DATA', color: 'text-blue-500' },
                  no_match: { label: 'NO EMAILS FOUND', color: 'text-yellow-600' },
                  no_pdfs: { label: 'NO PDFs', color: 'text-yellow-600' },
                  no_transactions: { label: 'PARSE EMPTY', color: 'text-orange-500' },
                  password_error: { label: 'WRONG PASSWORD', color: 'text-red-500' },
                  parse_error: { label: 'PARSE FAILED', color: 'text-red-500' },
                  failed: { label: 'FAILED', color: 'text-red-500' },
                };
                const sc = statusConfig[log.status] || { label: log.status?.toUpperCase(), color: 'text-gray-500' };

                return (
                  <div key={i} data-testid={`sync-log-${i}`} className="rounded-lg p-3 border text-sm" style={{ background: 'var(--app-card-bg)', borderColor: 'var(--app-card-border)' }}>
                    <div className="flex justify-between items-center mb-1.5">
                      <span className={`text-xs font-semibold uppercase tracking-wide ${sc.color}`}>
                        {sc.label}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>
                        {new Date(log.synced_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex gap-4 text-xs flex-wrap" style={{ color: 'var(--app-text-secondary)' }}>
                      {log.imported > 0 && (
                        <span>New: <strong className="text-green-600">{log.imported}</strong></span>
                      )}
                      {log.skipped > 0 && (
                        <span>Already synced: <strong style={{ color: 'var(--app-text)' }}>{log.skipped}</strong></span>
                      )}
                      {log.emails_matched !== undefined && log.emails_matched > 0 && (
                        <span>Emails: <strong style={{ color: 'var(--app-text)' }}>{log.emails_matched}</strong></span>
                      )}
                      {log.files?.length > 0 && (
                        <span>PDFs: <strong style={{ color: 'var(--app-text)' }}>{log.files.length}</strong></span>
                      )}
                    </div>
                    {log.error && (
                      <p className="mt-1.5 text-xs text-red-500">{log.error}</p>
                    )}
                    {log.status === 'password_error' && (
                      <p className="mt-1 text-xs text-red-400">
                        Edit this account and set the correct PDF password, then re-sync.
                      </p>
                    )}
                    {log.status === 'no_match' && (
                      <p className="mt-1 text-xs text-yellow-600">
                        Edit the account's email filter to match your bank statement email subjects.
                      </p>
                    )}
                    {log.status === 'parse_error' && (
                      <p className="mt-1 text-xs text-orange-500">
                        Configure a custom parser for this account via the parser builder.
                      </p>
                    )}
                    {log.files?.length > 0 && (
                      <div className="mt-2 space-y-1 border-t pt-2" style={{ borderColor: 'var(--app-card-border)' }}>
                        {log.files.map((f, j) => {
                          const fColor = f.status === 'imported' ? 'text-green-600'
                            : f.status === 'all_duplicates' ? 'text-blue-500'
                            : f.status === 'password_error' ? 'text-red-500'
                            : f.status === 'parse_error' ? 'text-red-500'
                            : 'text-yellow-600';
                          const fLabel = f.status === 'imported' ? `${f.transactions_imported} new`
                            : f.status === 'all_duplicates' ? `${f.transactions_found} existing`
                            : f.status === 'password_error' ? 'password error'
                            : f.status === 'parse_error' ? 'parse failed'
                            : '0 txns';
                          return (
                            <div key={j} className="flex items-center justify-between text-xs">
                              <span className="truncate flex-1 mr-2" style={{ color: 'var(--app-text-muted)' }}>{f.filename}</span>
                              <span className={`shrink-0 font-medium ${fColor}`}>{fLabel}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Sync Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle style={{ color: 'var(--app-text)' }}>
              Sync Preview — {previewData?.account_name}
            </DialogTitle>
          </DialogHeader>
          {previewData && (
            <div className="space-y-4">
              {/* Filters used */}
              <div className="flex gap-3 flex-wrap text-xs" style={{ color: 'var(--app-text-muted)' }}>
                <span>Subject: <strong style={{ color: 'var(--app-text)' }}>{previewData.filter_used}</strong></span>
                {previewData.from_filter && <span>From: <strong style={{ color: 'var(--app-text)' }}>{previewData.from_filter}</strong></span>}
                {previewData.sync_since && <span>Since: <strong style={{ color: 'var(--app-text)' }}>{previewData.sync_since}</strong></span>}
              </div>

              {/* Summary cards */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {[
                  { label: 'IMAP Results', value: previewData.summary.total_imap_results || previewData.summary.total_emails, color: 'var(--app-text-muted)' },
                  { label: 'After Date Filter', value: previewData.summary.total_emails, color: 'var(--app-text)' },
                  { label: 'New Emails', value: previewData.summary.new_emails, color: '#5C745A' },
                  { label: 'Already Synced', value: previewData.summary.already_synced, color: '#7CA1A6' },
                  { label: 'New Transactions', value: previewData.summary.total_transactions, color: 'var(--app-accent)' },
                ].map((c, i) => (
                  <div key={i} className="rounded-lg p-3 text-center" style={{ background: 'var(--app-badge-bg)' }}>
                    <div className="text-[10px] uppercase tracking-[0.15em]" style={{ color: 'var(--app-text-muted)' }}>{c.label}</div>
                    <div className="text-xl font-heading mt-0.5" style={{ color: c.color }}>{c.value}</div>
                  </div>
                ))}
              </div>
              {previewData.summary.skipped_by_date_filter > 0 && (
                <div className="p-2 rounded-lg text-xs" style={{ background: 'var(--app-badge-bg)', color: 'var(--app-text-secondary)' }}>
                  {previewData.summary.skipped_by_date_filter} older email(s) filtered out by "Sync since" date ({previewData.sync_since})
                </div>
              )}
              {previewData.summary.password_errors > 0 && (
                <div className="p-2 rounded-lg bg-red-50 text-red-600 text-xs">
                  {previewData.summary.password_errors} PDF(s) couldn't be opened — check the PDF password on this account.
                </div>
              )}

              {/* Email list */}
              <div className="space-y-2">
                <h4 className="text-xs uppercase tracking-[0.15em] font-medium" style={{ color: 'var(--app-text-secondary)' }}>
                  Emails ({previewData.emails.length})
                </h4>
                {previewData.emails.map((email, i) => (
                  <div key={i} data-testid={`preview-email-${i}`}
                    className="rounded-lg p-3 border text-sm"
                    style={{
                      background: email.already_synced ? 'var(--app-badge-bg)' : 'var(--app-card-bg)',
                      borderColor: 'var(--app-card-border)',
                      opacity: email.already_synced ? 0.6 : 1
                    }}>
                    <div className="flex justify-between items-start gap-2 mb-1">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate" style={{ color: 'var(--app-text)' }}>{email.subject || '(no subject)'}</div>
                        <div className="text-xs mt-0.5" style={{ color: 'var(--app-text-muted)' }}>
                          From: {email.from} | {email.date}
                        </div>
                      </div>
                      {email.already_synced ? (
                        <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 font-medium">SYNCED</span>
                      ) : (
                        <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-600 font-medium">NEW</span>
                      )}
                    </div>
                    {email.pdfs.length > 0 ? (
                      <div className="mt-2 space-y-1">
                        {email.pdfs.map((pdf, j) => {
                          const statusColor = pdf.parse_status === 'ok' ? 'text-green-600'
                            : pdf.parse_status === 'password_error' ? 'text-red-500'
                            : pdf.parse_status === 'parse_error' ? 'text-red-500'
                            : pdf.parse_status === 'empty' ? 'text-yellow-600'
                            : 'text-gray-400';
                          const statusLabel = pdf.parse_status === 'ok' ? `${pdf.transactions_found} txns`
                            : pdf.parse_status === 'password_error' ? 'wrong password'
                            : pdf.parse_status === 'parse_error' ? 'parse failed'
                            : pdf.parse_status === 'empty' ? '0 txns'
                            : 'unknown';
                          return (
                            <div key={j} className="flex items-center justify-between text-xs pl-2 border-l-2" style={{ borderColor: 'var(--app-card-border)' }}>
                              <span className="truncate flex-1 mr-2" style={{ color: 'var(--app-text-secondary)' }}>
                                {pdf.filename} <span style={{ color: 'var(--app-text-muted)' }}>({pdf.size_kb} KB)</span>
                              </span>
                              <span className={`shrink-0 font-medium ${statusColor}`}>{statusLabel}</span>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>No PDF attachments</p>
                    )}
                  </div>
                ))}
              </div>
              {previewData.emails.length === 0 && (
                <p className="text-center py-6 text-sm" style={{ color: 'var(--app-text-muted)' }}>
                  No emails matched the filters. Try adjusting the subject filter or from filter.
                </p>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-red-600">Delete Account</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--app-text)' }}>
              Are you sure you want to delete <strong>{deleteTarget?.name}</strong>?
            </p>
            <div className="p-3 rounded-lg text-xs space-y-1" style={{ background: 'var(--app-badge-bg)', color: 'var(--app-text-secondary)' }}>
              <p>This will permanently delete:</p>
              <ul className="list-disc list-inside space-y-0.5 ml-1">
                <li>The account and its settings</li>
                <li>All transactions in this account</li>
                <li>All sync history and processed emails</li>
              </ul>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button variant="outline" onClick={() => setDeleteTarget(null)}
                data-testid="cancel-delete-btn"
                className="rounded-lg border" style={{ borderColor: 'var(--app-card-border)' }}>
                Cancel
              </Button>
              <Button onClick={() => handleDelete(deleteTarget?.id)}
                data-testid="confirm-delete-account-btn"
                className="bg-red-600 hover:bg-red-700 text-white rounded-lg">
                Delete Account
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Accounts;
