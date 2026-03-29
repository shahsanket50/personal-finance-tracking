import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { EnvelopeSimple, MagnifyingGlass, DownloadSimple, UploadSimple, CloudArrowUp, Check } from '@phosphor-icons/react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Settings = () => {
  const [emailConfig, setEmailConfig] = useState({ imap_server: 'imap.gmail.com', email_address: '', app_password: '' });
  const [emailConfigured, setEmailConfigured] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResults, setScanResults] = useState(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);

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
          app_password: ''
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
        <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
          Settings
        </h2>
        <p className="text-sm mt-1" style={{ color: '#78716C' }}>Email scanning, backup & restore</p>
      </div>

      {/* Email Configuration */}
      <div className="bg-white border border-[#E5E2DC] rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: '#1C1917' }}>
          <EnvelopeSimple size={20} className="inline mr-2" style={{ color: '#5C745A' }} />
          Email Auto-Scan
        </h3>
        <p className="text-sm mb-4" style={{ color: '#78716C' }}>
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
            <p className="text-xs mt-1" style={{ color: '#A8A29E' }}>
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
          <div className="flex gap-3">
            <Button
              type="submit"
              disabled={saving}
              data-testid="save-email-config-btn"
              className="bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
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
          <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: '#5C745A' }}>
            <Check size={16} />
            Email configured. Set email filters on each account, then click "Scan Inbox".
          </div>
        )}

        {scanResults && (
          <div className="mt-4 p-4 bg-[#F9F8F6] rounded-lg border border-[#E5E2DC]">
            <p className="font-medium text-sm mb-2" style={{ color: '#1C1917' }}>{scanResults.message}</p>
            {scanResults.details?.length > 0 && (
              <div className="space-y-1">
                {scanResults.details.map((d, i) => (
                  <p key={i} className="text-xs" style={{ color: '#78716C' }}>
                    {d.account}: {d.file} — {d.imported} imported ({d.found} found)
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Backup & Restore */}
      <div className="bg-white border border-[#E5E2DC] rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-1" style={{ color: '#1C1917' }}>
          <CloudArrowUp size={20} className="inline mr-2" style={{ color: '#5C745A' }} />
          Backup & Restore
        </h3>
        <p className="text-sm mb-4" style={{ color: '#78716C' }}>
          Export all your data as JSON or restore from a previous backup. No data is ever lost.
        </p>
        <div className="flex gap-3 flex-wrap">
          <Button
            onClick={handleExportBackup}
            data-testid="export-backup-settings-btn"
            className="bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
          >
            <DownloadSimple size={18} className="mr-2" />
            Download Backup
          </Button>
          <label>
            <Button
              as="span"
              disabled={importing}
              data-testid="import-backup-btn"
              className="bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg cursor-pointer"
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
    </div>
  );
};

export default Settings;
