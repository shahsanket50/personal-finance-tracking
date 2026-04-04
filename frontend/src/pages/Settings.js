import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  EnvelopeSimple, MagnifyingGlass, DownloadSimple, UploadSimple, CloudArrowUp, Check,
  Palette, AndroidLogo, Trash, Warning, Buildings, CalendarBlank, ArrowsClockwise, Tag
} from '@phosphor-icons/react';
import { useTheme } from '../contexts/ThemeContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Settings = () => {
  const { theme, setTheme, themes } = useTheme();
  const [activeTab, setActiveTab] = useState('tracker');
  const [emailConfig, setEmailConfig] = useState({ imap_server: 'imap.gmail.com', email_address: '', app_password: '', sync_since: '' });
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [resetting, setResetting] = useState(false);
  // Accounting state
  const [company, setCompany] = useState(null);
  const [companyForm, setCompanyForm] = useState({ name: '', address: '', gstin: '', pan: '', cin: '', fy_start_month: 4 });
  const [companyLoading, setCompanyLoading] = useState(false);
  const [fys, setFys] = useState([]);
  const [currentFy, setCurrentFy] = useState('');
  const [restoringCats, setRestoringCats] = useState(false);
  const [catCount, setCatCount] = useState(0);

  useEffect(() => { loadEmailConfig(); loadCompany(); loadCategories(); }, []);

  const loadEmailConfig = async () => {
    try {
      const res = await axios.get(`${API}/email-config`);
      if (res.data.configured) {
        setEmailConfigured(true);
        setEmailConfig(prev => ({
          ...prev,
          imap_server: res.data.imap_server,
          email_address: res.data.email_address,
          app_password: '',
          sync_since: res.data.sync_since || ''
        }));
      }
    } catch {}
  };

  const loadCompany = async () => {
    try {
      const [compRes, fyRes] = await Promise.all([
        axios.get(`${API}/company`),
        axios.get(`${API}/financial-years`),
      ]);
      setCompany(compRes.data);
      setCompanyForm({
        name: compRes.data.name || '',
        address: compRes.data.address || '',
        gstin: compRes.data.gstin || '',
        pan: compRes.data.pan || '',
        cin: compRes.data.cin || '',
        fy_start_month: compRes.data.fy_start_month || 4,
      });
      setFys(fyRes.data.years || []);
      setCurrentFy(fyRes.data.current_fy || '');
    } catch {}
  };

  const loadCategories = async () => {
    try {
      const res = await axios.get(`${API}/categories`);
      setCatCount(res.data.length);
    } catch {}
  };

  const saveEmailConfig = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await axios.post(`${API}/email-config`, emailConfig);
      toast.success('Email configuration saved');
      setEmailConfigured(true);
    } catch {
      toast.error('Failed to save email config');
    } finally {
      setSaving(false);
    }
  };

  const scanInbox = async () => {
    setScanning(true);
    setScanResults(null);
    try {
      const res = await axios.post(`${API}/email-scan`);
      setScanResults(res.data);
      toast.success(res.data.message);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleExportBackup = async () => {
    try {
      const res = await axios.get(`${API}/backup/export`);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `moneyinsights-backup-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Backup downloaded');
    } catch {
      toast.error('Export failed');
    }
  };

  const handleImportBackup = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const res = await axios.post(`${API}/backup/import`, data);
      toast.success(`Restored: ${res.data.imported.accounts} accounts, ${res.data.imported.transactions} transactions, ${res.data.imported.categories} categories`);
    } catch {
      toast.error('Import failed. Check file format.');
    } finally {
      setImporting(false);
      e.target.value = '';
    }
  };

  const saveCompany = async () => {
    setCompanyLoading(true);
    try {
      await axios.put(`${API}/company`, companyForm);
      toast.success('Company details saved');
      loadCompany();
    } catch {
      toast.error('Failed to save company');
    } finally {
      setCompanyLoading(false);
    }
  };

  const restoreCategories = async () => {
    setRestoringCats(true);
    try {
      const res = await axios.post(`${API}/categories/restore-defaults`);
      toast.success(res.data.message);
      loadCategories();
    } catch {
      toast.error('Failed to restore categories');
    } finally {
      setRestoringCats(false);
    }
  };

  const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--app-text)' }}>Settings</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Manage your application preferences</p>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 border-b pb-0" style={{ borderColor: 'var(--app-border)' }}>
        {[
          { key: 'tracker', label: 'Finance Tracker' },
          { key: 'accounting', label: 'Accounting' },
          { key: 'common', label: 'Appearance & Data' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className="px-4 py-2.5 text-sm font-medium transition-colors relative"
            style={{ color: activeTab === tab.key ? 'var(--app-accent)' : 'var(--app-text-muted)' }}
            data-testid={`settings-tab-${tab.key}`}
          >
            {tab.label}
            {activeTab === tab.key && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full" style={{ background: 'var(--app-accent)' }} />
            )}
          </button>
        ))}
      </div>

      {/* ═══ Finance Tracker Section ═══ */}
      {activeTab === 'tracker' && (
        <div className="space-y-8">
          {/* Email Configuration */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <EnvelopeSimple size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Email Auto-Scan
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              Connect your email to automatically download and parse bank statements. Uses IMAP with App Passwords.
            </p>
            <form onSubmit={saveEmailConfig} className="space-y-4 max-w-lg">
              <div>
                <Label htmlFor="email">Email Address</Label>
                <Input id="email" type="email" data-testid="email-config-address" value={emailConfig.email_address}
                  onChange={e => setEmailConfig({...emailConfig, email_address: e.target.value})} placeholder="your.email@gmail.com" required />
              </div>
              <div>
                <Label htmlFor="app_password">App Password</Label>
                <Input id="app_password" type="password" data-testid="email-config-password" value={emailConfig.app_password}
                  onChange={e => setEmailConfig({...emailConfig, app_password: e.target.value})}
                  placeholder={emailConfigured ? '••••••••••••' : 'Google App Password'} required={!emailConfigured} />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>
                  Generate at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="underline text-blue-500">Google App Passwords</a>. Requires 2FA.
                </p>
              </div>
              <div>
                <Label htmlFor="imap">IMAP Server</Label>
                <Input id="imap" data-testid="email-config-imap" value={emailConfig.imap_server}
                  onChange={e => setEmailConfig({...emailConfig, imap_server: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="sync_since">Sync emails since</Label>
                <Input id="sync_since" type="date" data-testid="email-config-sync-since" value={emailConfig.sync_since}
                  onChange={e => setEmailConfig({...emailConfig, sync_since: e.target.value})} />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Only scan emails after this date. Leave blank for all.</p>
              </div>
              <div className="flex gap-3">
                <Button type="submit" disabled={saving} data-testid="save-email-config-btn" className="themed-btn-primary rounded-lg">
                  {saving ? 'Saving...' : emailConfigured ? 'Update Config' : 'Save Config'}
                </Button>
                {emailConfigured && (
                  <Button type="button" onClick={scanInbox} disabled={scanning} data-testid="scan-inbox-btn"
                    className="bg-blue-600 text-white hover:bg-blue-700 rounded-lg">
                    <MagnifyingGlass size={18} className="mr-2" />
                    {scanning ? 'Scanning...' : 'Scan Inbox'}
                  </Button>
                )}
              </div>
            </form>
            {emailConfigured && (
              <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: 'var(--app-accent)' }}>
                <Check size={16} /> Email configured. Set email filters on each account, then click "Scan Inbox".
              </div>
            )}
            {scanResults && (
              <div className="mt-4 p-4 themed-badge rounded-lg border border-[var(--app-card-border)]">
                <p className="font-medium text-sm mb-2" style={{ color: 'var(--app-text)' }}>{scanResults.message}</p>
                {scanResults.details?.length > 0 && (
                  <div className="space-y-1">
                    {scanResults.details.map((d, i) => (
                      <p key={i} className="text-xs" style={{ color: 'var(--app-text-secondary)' }}>
                        {d.account}: {d.file} — {d.imported} imported ({d.found} found)
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Categories Management */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <Tag size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Categories
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              You have <strong>{catCount}</strong> categories. Missing default categories? Restore them with one click.
            </p>
            <Button onClick={restoreCategories} disabled={restoringCats} data-testid="restore-categories-btn"
              className="themed-btn-primary rounded-lg">
              <ArrowsClockwise size={18} className="mr-2" />
              {restoringCats ? 'Restoring...' : 'Restore Default Categories'}
            </Button>
          </div>
        </div>
      )}

      {/* ═══ Accounting Section ═══ */}
      {activeTab === 'accounting' && (
        <div className="space-y-8">
          {/* Company Details */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <Buildings size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Company Details
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              Your business identity for the accounting books
            </p>
            <div className="space-y-4 max-w-lg">
              <div>
                <Label>Company Name</Label>
                <Input value={companyForm.name} onChange={e => setCompanyForm(p => ({...p, name: e.target.value}))} data-testid="settings-company-name" />
              </div>
              <div>
                <Label>Address</Label>
                <Input value={companyForm.address} onChange={e => setCompanyForm(p => ({...p, address: e.target.value}))} data-testid="settings-company-address" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>GSTIN</Label>
                  <Input value={companyForm.gstin} onChange={e => setCompanyForm(p => ({...p, gstin: e.target.value}))} data-testid="settings-company-gstin" placeholder="22AAAAA0000A1Z5" />
                </div>
                <div>
                  <Label>PAN</Label>
                  <Input value={companyForm.pan} onChange={e => setCompanyForm(p => ({...p, pan: e.target.value}))} data-testid="settings-company-pan" placeholder="AAAAA0000A" />
                </div>
              </div>
              <div>
                <Label>CIN</Label>
                <Input value={companyForm.cin} onChange={e => setCompanyForm(p => ({...p, cin: e.target.value}))} placeholder="Optional" />
              </div>
              <Button onClick={saveCompany} disabled={companyLoading} data-testid="save-company-settings-btn" className="themed-btn-primary rounded-lg">
                {companyLoading ? 'Saving...' : 'Save Company Details'}
              </Button>
            </div>
          </div>

          {/* Financial Year */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <CalendarBlank size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Financial Year
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              Current FY: <strong style={{ color: 'var(--app-accent)' }}>{currentFy}</strong>
            </p>
            <div className="space-y-4 max-w-lg">
              <div>
                <Label>FY Starts In</Label>
                <Select value={String(companyForm.fy_start_month)} onValueChange={v => setCompanyForm(p => ({...p, fy_start_month: parseInt(v)}))}>
                  <SelectTrigger data-testid="fy-start-month-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {MONTHS.map((m, i) => <SelectItem key={i+1} value={String(i+1)}>{m}</SelectItem>)}
                  </SelectContent>
                </Select>
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Indian standard: April (month 4). Change and save company to update.</p>
              </div>
              {fys.length > 0 && (
                <div>
                  <Label className="mb-2 block">Available Financial Years</Label>
                  <div className="space-y-1.5">
                    {fys.map(fy => (
                      <div key={fy.label} className="flex items-center justify-between px-3 py-2 rounded-lg border text-sm"
                        style={{
                          borderColor: fy.label === currentFy ? 'var(--app-accent)' : 'var(--app-border)',
                          background: fy.label === currentFy ? 'var(--app-accent-light)' : 'var(--app-surface)',
                        }}
                        data-testid={`fy-${fy.label}`}
                      >
                        <span className="font-medium" style={{ color: fy.label === currentFy ? 'var(--app-accent)' : 'var(--app-text)' }}>
                          {fy.label} {fy.label === currentFy && <span className="text-xs">(current)</span>}
                        </span>
                        <span className="text-xs font-mono" style={{ color: 'var(--app-text-muted)' }}>{fy.start} to {fy.end}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Sync Transactions to Accounting */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <ArrowsClockwise size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Sync to Accounting
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              Convert all Finance Tracker transactions into double-entry vouchers.
            </p>
            <Button
              data-testid="migrate-accounting-btn"
              className="themed-btn-primary rounded-lg"
              onClick={async () => {
                try {
                  const res = await axios.post(`${API}/migrate-to-accounting`);
                  toast.success(res.data.message);
                } catch { toast.error('Migration failed'); }
              }}
            >
              <ArrowsClockwise size={18} className="mr-2" /> Sync Transactions to Vouchers
            </Button>
          </div>
        </div>
      )}

      {/* ═══ Common Section (Appearance & Data) ═══ */}
      {activeTab === 'common' && (
        <div className="space-y-8">
          {/* Theme Picker */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <Palette size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Appearance
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>Choose a theme. Changes apply instantly.</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {Object.entries(themes).map(([key, t]) => (
                <button key={key} onClick={() => { setTheme(key); toast.success(`Switched to ${t.name} theme`); }}
                  data-testid={`theme-setting-${key}`}
                  className="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200"
                  style={{
                    borderColor: theme === key ? 'var(--app-accent)' : 'var(--app-card-border)',
                    background: theme === key ? 'var(--app-accent-light)' : 'var(--app-card-bg)',
                  }}>
                  <div className="w-10 h-10 rounded-full border-2 shadow-sm"
                    style={{ background: t.preview, borderColor: theme === key ? 'var(--app-accent)' : 'var(--app-card-border)' }} />
                  <span className="text-sm font-medium" style={{ color: theme === key ? 'var(--app-accent)' : 'var(--app-text-secondary)' }}>{t.name}</span>
                  {theme === key && <Check size={14} weight="bold" style={{ color: 'var(--app-accent)' }} />}
                </button>
              ))}
            </div>
          </div>

          {/* Backup & Restore */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <CloudArrowUp size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Backup & Restore
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>Export all data or restore from backup.</p>
            <div className="flex gap-3 flex-wrap">
              <Button onClick={handleExportBackup} data-testid="export-backup-settings-btn" className="themed-btn-primary rounded-lg">
                <DownloadSimple size={18} className="mr-2" /> Download Backup
              </Button>
              <label>
                <Button as="span" disabled={importing} data-testid="import-backup-btn"
                  className="themed-badge text-[#1C1917] hover:bg-[#E5E2DC] border border-[var(--app-card-border)] rounded-lg cursor-pointer"
                  onClick={() => document.getElementById('backup-file-input').click()}>
                  <UploadSimple size={18} className="mr-2" /> {importing ? 'Importing...' : 'Restore from Backup'}
                </Button>
                <input id="backup-file-input" type="file" accept=".json" className="hidden" onChange={handleImportBackup} />
              </label>
            </div>
          </div>

          {/* Mobile App */}
          <div className="themed-card rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
              <AndroidLogo size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
              Mobile App
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>Install MoneyInsights on your Android device via PWA.</p>
            <div className="flex gap-3 flex-wrap items-center">
              <Button data-testid="download-apk-btn" className="themed-btn-primary rounded-lg"
                onClick={() => toast.info('Use "Add to Home Screen" in your browser for a native-like experience.')}>
                <DownloadSimple size={18} className="mr-2" /> Download APK
              </Button>
              <span className="text-xs px-2 py-1 rounded-full" style={{ background: 'var(--app-badge-bg)', color: 'var(--app-text-muted)' }}>Coming soon</span>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="rounded-lg p-6 border-2 border-red-200" style={{ background: 'var(--app-card-bg)' }}>
            <h3 className="text-lg font-semibold mb-1 text-red-600">
              <Trash size={20} className="inline mr-2" /> Danger Zone
            </h3>
            <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
              Reset ALL data — accounts, transactions, categories, sync history, vouchers, ledgers. Email config preserved.
            </p>
            <Button data-testid="reset-all-data-btn" onClick={() => setResetOpen(true)}
              className="bg-red-600 hover:bg-red-700 text-white rounded-lg">
              <Warning size={18} className="mr-2" /> Reset All Data
            </Button>
          </div>
        </div>
      )}

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetOpen} onOpenChange={(v) => { if (!v) { setResetOpen(false); setResetConfirmText(''); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-red-600">Reset All Data</DialogTitle>
            <DialogDescription>This action cannot be undone.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--app-text)' }}>This will permanently delete:</p>
            <div className="p-3 rounded-lg text-xs space-y-1 bg-red-50 text-red-700">
              <ul className="list-disc list-inside space-y-0.5">
                <li>All accounts & transactions</li>
                <li>All custom categories</li>
                <li>All vouchers, ledgers & accounting data</li>
                <li>All sync history & processed emails</li>
              </ul>
            </div>
            <div>
              <Label className="text-sm">Type <strong>RESET</strong> to confirm:</Label>
              <Input data-testid="reset-confirm-input" value={resetConfirmText} onChange={e => setResetConfirmText(e.target.value)}
                placeholder="Type RESET" className="mt-1" />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button variant="outline" onClick={() => { setResetOpen(false); setResetConfirmText(''); }}
                className="rounded-lg border" style={{ borderColor: 'var(--app-card-border)' }}>Cancel</Button>
              <Button disabled={resetConfirmText !== 'RESET' || resetting} data-testid="confirm-reset-btn"
                onClick={async () => {
                  setResetting(true);
                  try {
                    const res = await axios.post(`${API}/reset-all-data`);
                    toast.success(res.data.message);
                    setResetOpen(false);
                    setResetConfirmText('');
                  } catch { toast.error('Reset failed'); }
                  finally { setResetting(false); }
                }}
                className="bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50">
                {resetting ? 'Resetting...' : 'Reset Everything'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Settings;
