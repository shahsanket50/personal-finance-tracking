import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { UploadSimple, FileCsv, FilePdf } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Upload = () => {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
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
      const endpoint = file.name.endsWith('.csv') ? 'import-csv' : 'upload-statement';
      const res = await axios.post(`${API}/${endpoint}?account_id=${selectedAccount}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(res.data.message);
      if (res.data.note) {
        toast.info(res.data.note);
      }
      
      setFile(null);
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
        <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
          Upload Statements
        </h2>
        <p className="text-sm mt-1" style={{ color: '#78716C' }}>Import transactions from PDF or CSV files</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Form */}
        <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
          <h3 className="font-heading text-xl mb-4" style={{ color: '#1C1917' }}>Upload File</h3>
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
              <Label htmlFor="file-input">Select File (PDF or CSV)</Label>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.csv"
                onChange={handleFileChange}
                data-testid="file-input"
                className="mt-2 block w-full text-sm border border-[#E5E2DC] rounded-lg cursor-pointer focus:outline-none p-2"
                style={{ color: '#1C1917' }}
              />
              {file && (
                <p className="mt-2 text-sm" style={{ color: '#5C745A' }}>
                  Selected: {file.name}
                </p>
              )}
            </div>

            <Button 
              type="submit" 
              disabled={uploading || !file || !selectedAccount}
              data-testid="upload-submit-btn"
              className="w-full bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg disabled:opacity-50"
            >
              <UploadSimple size={18} className="mr-2" />
              {uploading ? 'Uploading...' : 'Upload File'}
            </Button>
          </form>
        </div>

        {/* Instructions */}
        <div className="space-y-4">
          <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FileCsv size={24} style={{ color: '#5C745A' }} />
              <h3 className="font-heading text-lg" style={{ color: '#1C1917' }}>CSV Format</h3>
            </div>
            <p className="text-sm mb-2" style={{ color: '#78716C' }}>Your CSV file should have the following columns:</p>
            <div className="bg-[#F9F8F6] p-3 rounded font-mono text-xs" style={{ color: '#1C1917' }}>
              date,description,amount,type
            </div>
            <p className="text-sm mt-2" style={{ color: '#78716C' }}>Example:</p>
            <div className="bg-[#F9F8F6] p-3 rounded font-mono text-xs mt-2" style={{ color: '#1C1917' }}>
              2025-01-15,Grocery Store,2500.50,debit<br />
              2025-01-16,Salary Deposit,50000.00,credit
            </div>
          </div>

          <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-3">
              <FilePdf size={24} style={{ color: '#C06B52' }} />
              <h3 className="font-heading text-lg" style={{ color: '#1C1917' }}>PDF Statements</h3>
            </div>
            <p className="text-sm" style={{ color: '#78716C' }}>
              PDF parsing is currently in beta. The system will extract text from your PDF statement. 
              For best results, use CSV format or manually add transactions.
            </p>
            <div className="mt-4 p-3 bg-[#FEF3C7] border border-[#F59E0B] rounded-lg">
              <p className="text-sm" style={{ color: '#92400E' }}>
                <strong>Tip:</strong> Most banks allow you to download CSV or Excel versions of your statements, 
                which are more reliable for importing.
              </p>
            </div>
          </div>

          <div className="bg-white border border-[#E5E2DC] rounded-lg p-6 shadow-sm">
            <h3 className="font-heading text-lg mb-2" style={{ color: '#1C1917' }}>Sample CSV Download</h3>
            <p className="text-sm mb-3" style={{ color: '#78716C' }}>Download a sample CSV file to see the correct format:</p>
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
              className="bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
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
