import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { TreeStructure, Plus, PencilSimple, Trash, CaretRight, CaretDown, BookOpen } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const NATURE_COLORS = {
  asset: '#5C745A',
  liability: '#C06B52',
  income: '#7CA1A6',
  expense: '#D4A373',
};

const ChartOfAccounts = () => {
  const [groups, setGroups] = useState([]);
  const [ledgers, setLedgers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [ledgerDialogOpen, setLedgerDialogOpen] = useState(false);
  const [groupDialogOpen, setGroupDialogOpen] = useState(false);
  const [editingLedger, setEditingLedger] = useState(null);
  const [ledgerForm, setLedgerForm] = useState({ name: '', group_id: '', opening_balance: 0, opening_type: 'dr' });
  const [groupForm, setGroupForm] = useState({ name: '', parent_id: '', nature: 'expense' });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [gRes, lRes] = await Promise.all([
        axios.get(`${API}/account-groups`),
        axios.get(`${API}/ledgers`),
      ]);
      setGroups(gRes.data);
      setLedgers(lRes.data);
      if (expandedGroups.size === 0) {
        setExpandedGroups(new Set(gRes.data.filter(g => !g.parent_id).map(g => g.id)));
      }
    } catch {
      toast.error('Failed to load chart of accounts');
    } finally {
      setLoading(false);
    }
  };

  const tree = useMemo(() => {
    const groupMap = {};
    groups.forEach(g => { groupMap[g.id] = { ...g, children: [], ledgers: [] }; });
    ledgers.forEach(l => {
      if (groupMap[l.group_id]) groupMap[l.group_id].ledgers.push(l);
    });
    const roots = [];
    groups.forEach(g => {
      if (g.parent_id && groupMap[g.parent_id]) {
        groupMap[g.parent_id].children.push(groupMap[g.id]);
      } else if (!g.parent_id) {
        roots.push(groupMap[g.id]);
      }
    });
    roots.sort((a, b) => a.sort_order - b.sort_order);
    return roots;
  }, [groups, ledgers]);

  const toggleGroup = (id) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const openNewLedger = (groupId) => {
    setEditingLedger(null);
    setLedgerForm({ name: '', group_id: groupId, opening_balance: 0, opening_type: 'dr' });
    setLedgerDialogOpen(true);
  };

  const openEditLedger = (ledger) => {
    setEditingLedger(ledger);
    setLedgerForm({
      name: ledger.name,
      group_id: ledger.group_id,
      opening_balance: ledger.opening_balance || 0,
      opening_type: ledger.opening_type || 'dr',
    });
    setLedgerDialogOpen(true);
  };

  const saveLedger = async () => {
    if (!ledgerForm.name.trim()) return toast.error('Name is required');
    try {
      if (editingLedger) {
        await axios.put(`${API}/ledgers/${editingLedger.id}`, ledgerForm);
        toast.success('Ledger updated');
      } else {
        await axios.post(`${API}/ledgers`, ledgerForm);
        toast.success('Ledger created');
      }
      setLedgerDialogOpen(false);
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save ledger');
    }
  };

  const deleteLedger = async (id) => {
    if (!window.confirm('Delete this ledger?')) return;
    try {
      await axios.delete(`${API}/ledgers/${id}`);
      toast.success('Ledger deleted');
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete');
    }
  };

  const saveGroup = async () => {
    if (!groupForm.name.trim()) return toast.error('Name is required');
    try {
      await axios.post(`${API}/account-groups`, {
        name: groupForm.name,
        parent_id: groupForm.parent_id || null,
        nature: groupForm.nature,
      });
      toast.success('Group created');
      setGroupDialogOpen(false);
      loadData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create group');
    }
  };

  const renderGroup = (group, depth = 0) => {
    const isExpanded = expandedGroups.has(group.id);
    const hasChildren = group.children.length > 0 || group.ledgers.length > 0;

    return (
      <div key={group.id} data-testid={`group-${group.name.toLowerCase().replace(/\s+/g, '-')}`}>
        <div
          className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:opacity-80 transition-opacity border-b"
          style={{ paddingLeft: `${depth * 24 + 12}px`, borderColor: 'var(--app-border)' }}
          onClick={() => toggleGroup(group.id)}
        >
          {hasChildren ? (
            isExpanded ? <CaretDown size={14} style={{ color: 'var(--app-text-muted)' }} /> : <CaretRight size={14} style={{ color: 'var(--app-text-muted)' }} />
          ) : <span className="w-3.5" />}
          <TreeStructure size={16} style={{ color: NATURE_COLORS[group.nature] || 'var(--app-text-muted)' }} />
          <span className="font-medium text-sm flex-1" style={{ color: 'var(--app-text)' }}>{group.name}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wider"
            style={{ background: `${NATURE_COLORS[group.nature]}15`, color: NATURE_COLORS[group.nature] }}>
            {group.nature}
          </span>
          <button
            onClick={e => { e.stopPropagation(); openNewLedger(group.id); }}
            className="p-1 rounded hover:bg-black/5 transition-colors"
            title="Add ledger"
            data-testid={`add-ledger-${group.name.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <Plus size={14} style={{ color: 'var(--app-text-muted)' }} />
          </button>
        </div>
        {isExpanded && (
          <>
            {group.children.sort((a, b) => a.sort_order - b.sort_order).map(child => renderGroup(child, depth + 1))}
            {group.ledgers.map(ledger => (
              <div key={ledger.id}
                className="flex items-center gap-2 px-3 py-1.5 border-b hover:bg-black/[0.02] transition-colors"
                style={{ paddingLeft: `${(depth + 1) * 24 + 12}px`, borderColor: 'var(--app-border)' }}
                data-testid={`ledger-${ledger.name.toLowerCase().replace(/\s+/g, '-')}`}
              >
                <BookOpen size={14} style={{ color: 'var(--app-text-muted)' }} />
                <span className="text-sm flex-1" style={{ color: 'var(--app-text)' }}>{ledger.name}</span>
                {ledger.linked_account_id && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>linked</span>
                )}
                {ledger.opening_balance > 0 && (
                  <span className="text-xs font-mono" style={{ color: 'var(--app-text-muted)' }}>
                    {ledger.opening_balance.toLocaleString('en-IN')} {ledger.opening_type?.toUpperCase()}
                  </span>
                )}
                <button onClick={() => openEditLedger(ledger)} className="p-1 rounded hover:bg-black/5" data-testid={`edit-ledger-${ledger.id}`}>
                  <PencilSimple size={13} style={{ color: 'var(--app-text-muted)' }} />
                </button>
                <button onClick={() => deleteLedger(ledger.id)} className="p-1 rounded hover:bg-black/5" data-testid={`delete-ledger-${ledger.id}`}>
                  <Trash size={13} style={{ color: '#C06B52' }} />
                </button>
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="chart-of-accounts">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Chart of Accounts</h1>
          <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>{groups.length} groups, {ledgers.length} ledgers</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { setGroupForm({ name: '', parent_id: '', nature: 'expense' }); setGroupDialogOpen(true); }} data-testid="add-group-btn">
            <Plus size={16} className="mr-1" /> Add Group
          </Button>
        </div>
      </div>

      <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
        {tree.map(group => renderGroup(group))}
      </div>

      {/* Ledger Dialog */}
      <Dialog open={ledgerDialogOpen} onOpenChange={setLedgerDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingLedger ? 'Edit Ledger' : 'New Ledger'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <Label>Ledger Name</Label>
              <Input value={ledgerForm.name} onChange={e => setLedgerForm(p => ({ ...p, name: e.target.value }))} data-testid="ledger-name-input" />
            </div>
            <div>
              <Label>Under Group</Label>
              <Select value={ledgerForm.group_id} onValueChange={v => setLedgerForm(p => ({ ...p, group_id: v }))}>
                <SelectTrigger data-testid="ledger-group-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {groups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Opening Balance</Label>
                <Input type="number" value={ledgerForm.opening_balance} onChange={e => setLedgerForm(p => ({ ...p, opening_balance: parseFloat(e.target.value) || 0 }))} />
              </div>
              <div>
                <Label>Type</Label>
                <Select value={ledgerForm.opening_type} onValueChange={v => setLedgerForm(p => ({ ...p, opening_type: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dr">Debit (Dr)</SelectItem>
                    <SelectItem value="cr">Credit (Cr)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Button onClick={saveLedger} className="w-full" data-testid="save-ledger-btn">
              {editingLedger ? 'Update Ledger' : 'Create Ledger'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Group Dialog */}
      <Dialog open={groupDialogOpen} onOpenChange={setGroupDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Account Group</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 pt-2">
            <div>
              <Label>Group Name</Label>
              <Input value={groupForm.name} onChange={e => setGroupForm(p => ({ ...p, name: e.target.value }))} data-testid="group-name-input" />
            </div>
            <div>
              <Label>Parent Group (optional)</Label>
              <Select value={groupForm.parent_id} onValueChange={v => setGroupForm(p => ({ ...p, parent_id: v }))}>
                <SelectTrigger><SelectValue placeholder="None (root group)" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (root group)</SelectItem>
                  {groups.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Nature</Label>
              <Select value={groupForm.nature} onValueChange={v => setGroupForm(p => ({ ...p, nature: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="asset">Asset</SelectItem>
                  <SelectItem value="liability">Liability</SelectItem>
                  <SelectItem value="income">Income</SelectItem>
                  <SelectItem value="expense">Expense</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={saveGroup} className="w-full" data-testid="save-group-btn">Create Group</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ChartOfAccounts;
