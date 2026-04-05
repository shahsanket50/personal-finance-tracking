import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { UploadSimple, FileCsv, FilePdf, CheckCircle, XCircle, Tag, ArrowsClockwise, FileText } from '@phosphor-icons/react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Upload = () => {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [pdfPassword, setPdfPassword] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => { loadAccounts(); }, []);

  const loadAccounts = async () => {
    try {
      const res = await axios.get(`${API}/accounts`);
      setAccounts(res.data);
    } catch {
      toast.error('Failed to load accounts');
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !selectedAccount) {
      toast.error('Please select both file and account');
      return;
    }

    setUploading(true);
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const endpoint = file.name.endsWith('.csv') ? 'import-csv' : 'upload-statement';
      let url = `${API}/${endpoint}?account_id=${selectedAccount}`;
      if (endpoint === 'upload-statement' && pdfPassword) {
        url += `&password=${encodeURIComponent(pdfPassword)}`;
      }

      const res = await axios.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const accountName = accounts.find(a => a.id === selectedAccount)?.name || 'Unknown';
      setResult({
        success: true,
        fileName: file.name,
        accountName,
        message: res.data.message,
        imported: res.data.imported_count ?? 0,
        duplicates: res.data.duplicates_skipped ?? 0,
        totalFound: res.data.total_found ?? 0,
        categorized: res.data.categorized_count ?? 0,
        note: res.data.note || null,
      });

      setFile(null);
      setPdfPassword('');
      if (document.getElementById('file-input')) {
        document.getElementById('file-input').value = '';
      }
    } catch (err) {
      const accountName = accounts.find(a => a.id === selectedAccount)?.name || 'Unknown';
      setResult({
        success: false,
        fileName: file.name,
        accountName,
        message: err.response?.data?.detail || 'Upload failed',
        imported: 0,
        duplicates: 0,
        totalFound: 0,
        categorized: 0,
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--app-text)' }}>
          Upload Statements
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--app-text-secondary)' }}>Import transactions from PDF or CSV files</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Form */}
        <div className="space-y-4">
          <div className="themed-card rounded-lg p-6 shadow-sm">
            <h3 className="font-heading text-xl mb-4" style={{ color: 'var(--app-text)' }}>Upload File</h3>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <Label>Select Account</Label>
                <Select value={selectedAccount} onValueChange={setSelectedAccount}>
                  <SelectTrigger data-testid="upload-account-select">
                    <SelectValue placeholder="Choose an account" />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map(acc => (
                      <SelectItem key={acc.id} value={acc.id}>{acc.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="pdf-password">PDF Password (if protected - optional)</Label>
                <Input
                  id="pdf-password"
                  type="text"
                  data-testid="pdf-password-input"
                  value={pdfPassword}
                  onChange={e => setPdfPassword(e.target.value)}
                  placeholder="e.g., DDMMYYYY or last 4 digits"
                />
                <p className="text-xs mt-1" style={{ color: 'var(--app-text-secondary)' }}>
                  Leave blank if saved in account settings or not password-protected
                </p>
              </div>

              <div>
                <Label htmlFor="file-input">Select File (PDF or CSV)</Label>
                <input
                  id="file-input"
                  type="file"
                  accept=".pdf,.csv"
                  onChange={e => setFile(e.target.files[0])}
                  data-testid="file-input"
                  className="mt-2 block w-full text-sm border rounded-lg cursor-pointer focus:outline-none p-2"
                  style={{ color: 'var(--app-text)', borderColor: 'var(--app-border)' }}
                />
                {file && (
                  <p className="mt-2 text-sm flex items-center gap-1.5" style={{ color: 'var(--app-accent)' }}>
                    <FileText size={14} /> {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>

              <Button
                type="submit"
                disabled={uploading || !file || !selectedAccount}
                data-testid="upload-submit-btn"
                className="w-full themed-btn-primary rounded-lg disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <ArrowsClockwise size={18} className="mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <UploadSimple size={18} className="mr-2" />
                    Upload & Import
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Result Panel */}
          {result && (
            <div
              className="rounded-lg p-5 border-2 transition-all"
              style={{
                borderColor: result.success ? '#5C745A' : '#C06B52',
                background: result.success ? '#5C745A08' : '#C06B5208',
              }}
              data-testid="upload-result-panel"
            >
              <div className="flex items-center gap-2 mb-3">
                {result.success ? (
                  <CheckCircle size={22} weight="fill" color="#5C745A" />
                ) : (
                  <XCircle size={22} weight="fill" color="#C06B52" />
                )}
                <span className="font-semibold text-sm" style={{ color: result.success ? '#5C745A' : '#C06B52' }}>
                  {result.success ? 'Upload Successful' : 'Upload Failed'}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between py-1 border-b" style={{ borderColor: 'var(--app-border)' }}>
                  <span style={{ color: 'var(--app-text-muted)' }}>File</span>
                  <span className="font-mono text-xs" style={{ color: 'var(--app-text)' }}>{result.fileName}</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b" style={{ borderColor: 'var(--app-border)' }}>
                  <span style={{ color: 'var(--app-text-muted)' }}>Account</span>
                  <span style={{ color: 'var(--app-text)' }}>{result.accountName}</span>
                </div>

                {result.success && (
                  <>
                    <div className="flex items-center justify-between py-1 border-b" style={{ borderColor: 'var(--app-border)' }}>
                      <span style={{ color: 'var(--app-text-muted)' }}>Transactions Found</span>
                      <span className="font-bold" style={{ color: 'var(--app-text)' }}>{result.totalFound}</span>
                    </div>
                    <div className="flex items-center justify-between py-1 border-b" style={{ borderColor: 'var(--app-border)' }}>
                      <span style={{ color: 'var(--app-text-muted)' }}>Imported (new)</span>
                      <span className="font-bold" style={{ color: '#5C745A' }}>{result.imported}</span>
                    </div>
                    {result.duplicates > 0 && (
                      <div className="flex items-center justify-between py-1 border-b" style={{ borderColor: 'var(--app-border)' }}>
                        <span style={{ color: 'var(--app-text-muted)' }}>Duplicates Skipped</span>
                        <span className="font-mono text-xs" style={{ color: 'var(--app-text-muted)' }}>{result.duplicates}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between py-1">
                      <span className="flex items-center gap-1" style={{ color: 'var(--app-text-muted)' }}>
                        <Tag size={14} /> Auto-Categorized
                      </span>
                      <span className="font-bold" style={{ color: result.categorized > 0 ? '#7CA1A6' : 'var(--app-text-muted)' }}>
                        {result.categorized > 0 ? result.categorized : 'None'}
                      </span>
                    </div>
                  </>
                )}

                {!result.success && (
                  <div className="py-1">
                    <span className="text-xs" style={{ color: '#C06B52' }}>{result.message}</span>
                  </div>
                )}
              </div>

              {result.note && (
                <p className="mt-3 text-xs px-3 py-2 rounded" style={{ background: 'var(--app-accent-light)', color: 'var(--app-accent-text)' }}>
                  {result.note}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="space-y-4">
          <div className="themed-card rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FilePdf size={24} style={{ color: '#C06B52' }} />
              <h3 className="font-heading text-lg" style={{ color: 'var(--app-text)' }}>PDF Statements</h3>
            </div>
            <p className="text-sm mb-3" style={{ color: 'var(--app-text-secondary)' }}>
              Upload PDF statements from any bank. The system will auto-detect transaction patterns.
            </p>
            <ul className="text-sm space-y-1.5" style={{ color: 'var(--app-text-secondary)' }}>
              <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0" style={{ color: '#5C745A' }} /> Auto-detects common bank statement formats</li>
              <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0" style={{ color: '#5C745A' }} /> Uses custom parser if configured for the account</li>
              <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0" style={{ color: '#5C745A' }} /> Automatically skips duplicate transactions</li>
              <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0" style={{ color: '#5C745A' }} /> AI auto-categorizes imported transactions</li>
              <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0" style={{ color: '#5C745A' }} /> Auto-creates accounting vouchers (bridge)</li>
            </ul>
          </div>

          <div className="themed-card rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FileCsv size={24} style={{ color: 'var(--app-accent)' }} />
              <h3 className="font-heading text-lg" style={{ color: 'var(--app-text)' }}>CSV Format</h3>
            </div>
            <p className="text-sm mb-2" style={{ color: 'var(--app-text-secondary)' }}>Your CSV file should have the following columns:</p>
            <div className="p-3 rounded font-mono text-xs" style={{ background: 'var(--app-bg)', color: 'var(--app-text)', border: '1px solid var(--app-border)' }}>
              date,description,amount,type
            </div>
            <p className="text-sm mt-2" style={{ color: 'var(--app-text-secondary)' }}>Example:</p>
            <div className="p-3 rounded font-mono text-xs mt-1" style={{ background: 'var(--app-bg)', color: 'var(--app-text)', border: '1px solid var(--app-border)' }}>
              2025-01-15,Grocery Store,2500.50,debit<br />
              2025-01-16,Salary Deposit,50000.00,credit
            </div>
            <Button
              onClick={() => {
                const csvContent = 'date,description,amount,type\n2025-01-15,Grocery Store,2500.50,debit\n2025-01-16,Salary Deposit,50000.00,credit\n2025-01-17,Coffee Shop,450.00,debit';
                const blob = new Blob([csvContent], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'sample_transactions.csv';
                a.click();
              }}
              data-testid="download-sample-btn"
              variant="outline"
              className="mt-3 text-sm"
              size="sm"
            >
              <FileCsv size={16} className="mr-1.5" /> Download Sample CSV
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
