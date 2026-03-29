import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { UploadSimple, FileCsv, FilePdf } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Upload = () => {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [pdfPassword, setPdfPassword] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

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

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !selectedAccount) {
      toast.error('Please select both file and account');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      let endpoint = file.name.endsWith('.csv') ? 'import-csv' : 'upload-statement';
      let url = `${API}/${endpoint}?account_id=${selectedAccount}`;
      
      // Add password parameter for PDF uploads
      if (endpoint === 'upload-statement' && pdfPassword) {
        url += `&password=${encodeURIComponent(pdfPassword)}`;
      }
      
      const res = await axios.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(res.data.message);
      if (res.data.imported_count !== undefined) {
        toast.info(`Imported: ${res.data.imported_count} | Duplicates skipped: ${res.data.duplicates_skipped || 0}`);
      }
      if (res.data.note) {
        toast.info(res.data.note);
      }
      
      setFile(null);
      setPdfPassword('');
      if (document.getElementById('file-input')) {
        document.getElementById('file-input').value = '';
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed');
      console.error(err);
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
                onChange={handleFileChange}
                data-testid="file-input"
                className="mt-2 block w-full text-sm border border-[var(--app-card-border)] rounded-lg cursor-pointer focus:outline-none p-2"
                style={{ color: 'var(--app-text)' }}
              />
              {file && (
                <p className="mt-2 text-sm" style={{ color: 'var(--app-accent)' }}>
                  Selected: {file.name}
                </p>
              )}
            </div>

            <Button 
              type="submit" 
              disabled={uploading || !file || !selectedAccount}
              data-testid="upload-submit-btn"
              className="w-full themed-btn-primary rounded-lg disabled:opacity-50"
            >
              <UploadSimple size={18} className="mr-2" />
              {uploading ? 'Uploading...' : 'Upload File'}
            </Button>
          </form>
        </div>

        {/* Instructions */}
        <div className="space-y-4">
          <div className="themed-card rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FileCsv size={24} style={{ color: 'var(--app-accent)' }} />
              <h3 className="font-heading text-lg" style={{ color: 'var(--app-text)' }}>CSV Format</h3>
            </div>
            <p className="text-sm mb-2" style={{ color: 'var(--app-text-secondary)' }}>Your CSV file should have the following columns:</p>
            <div className="themed-badge p-3 rounded font-mono text-xs" style={{ color: 'var(--app-text)' }}>
              date,description,amount,type
            </div>
            <p className="text-sm mt-2" style={{ color: 'var(--app-text-secondary)' }}>Example:</p>
            <div className="themed-badge p-3 rounded font-mono text-xs mt-2" style={{ color: 'var(--app-text)' }}>
              2025-01-15,Grocery Store,2500.50,debit<br />
              2025-01-16,Salary Deposit,50000.00,credit
            </div>
          </div>

          <div className="themed-card rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FilePdf size={24} style={{ color: 'var(--app-danger)' }} />
              <h3 className="font-heading text-lg" style={{ color: 'var(--app-text)' }}>PDF Statements</h3>
            </div>
            <p className="text-sm mb-3" style={{ color: 'var(--app-text-secondary)' }}>
              Upload PDF statements from any bank. The system will auto-detect transaction patterns.
            </p>
            <div className="p-3 bg-[var(--app-accent-light)] border border-[var(--app-accent)] rounded-lg mb-3">
              <p className="text-sm" style={{ color: 'var(--app-accent-text)' }}>
                <strong>💡 Pro Tip:</strong> Use the <strong>Parser Builder</strong> (sparkle icon on Accounts page) to configure custom parsing for each account!
              </p>
            </div>
            <div className="text-sm mb-2" style={{ color: 'var(--app-text)', fontWeight: '500' }}>How it works:</div>
            <ul className="text-sm space-y-1" style={{ color: 'var(--app-text-secondary)' }}>
              <li>• Auto-detects common bank statement formats</li>
              <li>• Uses custom parser if configured for the account</li>
              <li>• Automatically skips duplicate transactions</li>
              <li>• Saves password to account for future uploads</li>
            </ul>
          </div>

          <div className="themed-card rounded-lg p-6 shadow-sm">
            <h3 className="font-heading text-lg mb-2" style={{ color: 'var(--app-text)' }}>Sample CSV Download</h3>
            <p className="text-sm mb-3" style={{ color: 'var(--app-text-secondary)' }}>Download a sample CSV file to see the correct format:</p>
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
              className="themed-badge text-[#1C1917] hover:bg-[#E5E2DC] border border-[var(--app-card-border)] rounded-lg"
            >
              <FileCsv size={18} className="mr-2" />
              Download Sample CSV
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
