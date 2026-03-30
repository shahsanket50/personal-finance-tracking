import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { EnvelopeSimple, MagnifyingGlass, DownloadSimple, UploadSimple, CloudArrowUp, Check, Palette, AndroidLogo, Trash, Warning } from '@phosphor-icons/react';
import { useTheme } from '../contexts/ThemeContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Settings = () => {
  const { theme, setTheme, themes } = useTheme();
  const [emailConfig, setEmailConfig] = useState({ imap_server: 'imap.gmail.com', email_address: '', app_password: '', sync_since: '' });
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetConfirmText, setResetConfirmText] = useState('');
  const [resetting, setResetting] = useState(false);

  useEffect(() => { loadEmailConfig(); }, []);

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

  const saveEmailConfig = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await axios.post(`${API}/email-config`, emailConfig);
      toast.success('Email configuration saved');
      setEmailConfigured(true);
    } catch (err) {
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
      const detail = err.response?.data?.detail || 'Scan failed';
      toast.error(detail);
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

  return (
    <div className="space-y-8">
      <div>
        <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--app-text)' }}>
          Settings
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Email scanning, backup, appearance & more</p>
      </div>

      {/* Email Configuration */}
      <div className="themed-card rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
          <EnvelopeSimple size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
          Email Auto-Scan
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
          Connect your email to automatically download and parse bank statements. Uses IMAP with App Passwords for secure access.
        </p>

        <form onSubmit={saveEmailConfig} className="space-y-4 max-w-lg">
          <div>
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              data-testid="email-config-address"
              value={emailConfig.email_address}
              onChange={e => setEmailConfig({...emailConfig, email_address: e.target.value})}
              placeholder="your.email@gmail.com"
              required
            />
          </div>
          <div>
            <Label htmlFor="app_password">App Password</Label>
            <Input
              id="app_password"
              type="password"
              data-testid="email-config-password"
              value={emailConfig.app_password}
              onChange={e => setEmailConfig({...emailConfig, app_password: e.target.value})}
              placeholder={emailConfigured ? '••••••••••••' : 'Google App Password'}
              required={!emailConfigured}
            />
            <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>
              Generate at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="underline text-blue-500">Google App Passwords</a>. Requires 2FA enabled.
            </p>
          </div>
          <div>
            <Label htmlFor="imap">IMAP Server</Label>
            <Input
              id="imap"
              data-testid="email-config-imap"
              value={emailConfig.imap_server}
              onChange={e => setEmailConfig({...emailConfig, imap_server: e.target.value})}
            />
          </div>
          <div>
            <Label htmlFor="sync_since">Sync emails since</Label>
            <Input
              id="sync_since"
              type="date"
              data-testid="email-config-sync-since"
              value={emailConfig.sync_since}
              onChange={e => setEmailConfig({...emailConfig, sync_since: e.target.value})}
            />
            <p className="text-xs mt-1" style={{ color: 'var(--app-text-muted)' }}>Only scan emails received after this date. Leave blank to scan all.</p>
          </div>
          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={saving}
              data-testid="save-email-config-btn"
              className="themed-btn-primary rounded-lg"
            >
              {saving ? 'Saving...' : emailConfigured ? 'Update Config' : 'Save Config'}
            </Button>
            {emailConfigured && (
              <Button
                type="button"
                onClick={scanInbox}
                disabled={scanning}
                data-testid="scan-inbox-btn"
                className="bg-blue-600 text-white hover:bg-blue-700 rounded-lg"
              >
                <MagnifyingGlass size={18} className="mr-2" />
                {scanning ? 'Scanning...' : 'Scan Inbox'}
              </Button>
            )}
          </div>
        </form>

        {emailConfigured && (
          <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: 'var(--app-accent)' }}>
            <Check size={16} />
            Email configured. Set email filters on each account, then click "Scan Inbox".
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

      {/* Backup & Restore */}
      <div className="themed-card rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
          <CloudArrowUp size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
          Backup & Restore
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
          Export all your data as JSON or restore from a previous backup. No data is ever lost.
        </p>
        <div className="flex gap-3 flex-wrap">
          <Button
            onClick={handleExportBackup}
            data-testid="export-backup-settings-btn"
            className="themed-btn-primary rounded-lg"
          >
            <DownloadSimple size={18} className="mr-2" />
            Download Backup
          </Button>
          <label>
            <Button
              as="span"
              disabled={importing}
              data-testid="import-backup-btn"
              className="themed-badge text-[#1C1917] hover:bg-[#E5E2DC] border border-[var(--app-card-border)] rounded-lg cursor-pointer"
              onClick={() => document.getElementById('backup-file-input').click()}
            >
              <UploadSimple size={18} className="mr-2" />
              {importing ? 'Importing...' : 'Restore from Backup'}
            </Button>
            <input
              id="backup-file-input"
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleImportBackup}
            />
          </label>
        </div>
      </div>

      {/* Theme Picker */}
      <div className="themed-card rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
          <Palette size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
          Appearance
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
          Choose a theme that suits your style. Changes apply instantly.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {Object.entries(themes).map(([key, t]) => (
            <button
              key={key}
              onClick={() => { setTheme(key); toast.success(`Switched to ${t.name} theme`); }}
              data-testid={`theme-setting-${key}`}
              className="flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all duration-200"
              style={{
                borderColor: theme === key ? 'var(--app-accent)' : 'var(--app-card-border)',
                background: theme === key ? 'var(--app-accent-light)' : 'var(--app-card-bg)',
              }}
            >
              <div
                className="w-10 h-10 rounded-full border-2 shadow-sm"
                style={{ background: t.preview, borderColor: theme === key ? 'var(--app-accent)' : 'var(--app-card-border)' }}
              />
              <span className="text-sm font-medium" style={{ color: theme === key ? 'var(--app-accent)' : 'var(--app-text-secondary)' }}>
                {t.name}
              </span>
              {theme === key && (
                <Check size={14} weight="bold" style={{ color: 'var(--app-accent)' }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Download APK */}
      <div className="themed-card rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: 'var(--app-text)' }}>
          <AndroidLogo size={20} className="inline mr-2" style={{ color: 'var(--app-accent)' }} />
          Mobile App
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
          Install MoneyInsights on your Android device. You can also install as a PWA by using "Add to Home Screen" in your browser.
        </p>
        <div className="flex gap-3 flex-wrap items-center">
          <Button
            data-testid="download-apk-btn"
            className="themed-btn-primary rounded-lg"
            onClick={() => toast.info('APK download will be available soon. For now, use "Add to Home Screen" in your browser for a native-like experience.')}
          >
            <DownloadSimple size={18} className="mr-2" />
            Download APK
          </Button>
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: 'var(--app-badge-bg)', color: 'var(--app-text-muted)' }}>
            Coming soon
          </span>
        </div>
      </div>

      {/* Danger Zone - Data Cleanup */}
      <div className="rounded-lg p-6 border-2 border-red-200" style={{ background: 'var(--app-card-bg)' }}>
        <h3 className="text-lg font-semibold mb-1 text-red-600">
          <Trash size={20} className="inline mr-2" />
          Danger Zone
        </h3>
        <p className="text-sm mb-4" style={{ color: 'var(--app-text-secondary)' }}>
          Reset all your data to start fresh. This will permanently delete all accounts, transactions, categories, and sync history. Your email configuration and user account will be preserved.
        </p>
        <Button
          data-testid="reset-all-data-btn"
          onClick={() => setResetOpen(true)}
          className="bg-red-600 hover:bg-red-700 text-white rounded-lg"
        >
          <Warning size={18} className="mr-2" />
          Reset All Data
        </Button>
      </div>

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetOpen} onOpenChange={(v) => { if (!v) { setResetOpen(false); setResetConfirmText(''); } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-red-600">Reset All Data</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--app-text)' }}>
              This will permanently delete:
            </p>
            <div className="p-3 rounded-lg text-xs space-y-1 bg-red-50 text-red-700">
              <ul className="list-disc list-inside space-y-0.5">
                <li>All accounts</li>
                <li>All transactions</li>
                <li>All custom categories</li>
                <li>All sync history & processed emails</li>
              </ul>
            </div>
            <div>
              <Label className="text-sm">Type <strong>RESET</strong> to confirm:</Label>
              <Input
                data-testid="reset-confirm-input"
                value={resetConfirmText}
                onChange={e => setResetConfirmText(e.target.value)}
                placeholder="Type RESET"
                className="mt-1"
              />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button variant="outline" onClick={() => { setResetOpen(false); setResetConfirmText(''); }}
                className="rounded-lg border" style={{ borderColor: 'var(--app-card-border)' }}>
                Cancel
              </Button>
              <Button
                disabled={resetConfirmText !== 'RESET' || resetting}
                data-testid="confirm-reset-btn"
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
                className="bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50"
              >
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
