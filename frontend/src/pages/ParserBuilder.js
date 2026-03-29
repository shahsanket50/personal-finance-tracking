import { useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { FileText, Code, Check, X, Sparkle } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ParserBuilder = ({ account, open, onClose, onSave }) => {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState('');
  const [extractedText, setExtractedText] = useState('');
  const [autoTransactions, setAutoTransactions] = useState([]);
  const [detectedStrategy, setDetectedStrategy] = useState('');
  const [allStrategies, setAllStrategies] = useState({});
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async () => {
    if (!file) {
      toast.error('Please select a PDF file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(
        `${API}/build-parser?account_id=${account.id}&password=${password}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      setExtractedText(res.data.text);
      setAutoTransactions(res.data.sample_transactions);
      setDetectedStrategy(res.data.detected_strategy || '');
      setAllStrategies(res.data.all_strategies || {});
      
      if (res.data.transactions_found > 0) {
        toast.success(`Auto-detected ${res.data.transactions_found} transactions!`);
        setStep(2);
      } else {
        toast.info('No transactions auto-detected. You can define a custom pattern.');
        setStep(2);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to process PDF');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAutoPattern = async () => {
    try {
      // Save the pattern, strategy and password
      await axios.post(`${API}/save-parser-pattern?account_id=${account.id}&password=${encodeURIComponent(password)}&strategy=${encodeURIComponent(detectedStrategy)}`);
      
      toast.success('Parser configured! Future uploads will use this setting.');
      onSave();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save pattern');
      console.error(err);
    }
  };

  const resetBuilder = () => {
    setStep(1);
    setFile(null);
    setPassword('');
    setExtractedText('');
    setAutoTransactions([]);
    setDetectedStrategy('');
    setAllStrategies({});
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <Sparkle size={24} style={{ color: '#5C745A' }} />
            Parser Builder - {account?.name}
          </DialogTitle>
        </DialogHeader>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 my-6">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-[#5C745A]' : 'text-[#A8A29E]'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? 'bg-[#5C745A] text-white' : 'bg-[#E5E2DC] text-[#A8A29E]'}`}>
              1
            </div>
            <span className="text-sm font-medium">Upload Sample</span>
          </div>
          <div className="w-12 h-0.5 bg-[#E5E2DC]" />
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-[#5C745A]' : 'text-[#A8A29E]'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? 'bg-[#5C745A] text-white' : 'bg-[#E5E2DC] text-[#A8A29E]'}`}>
              2
            </div>
            <span className="text-sm font-medium">Review & Save</span>
          </div>
        </div>

        {/* Step 1: Upload Sample PDF */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-[#E7F3F0] border border-[#5C745A] rounded-lg p-4">
              <p className="text-sm" style={{ color: '#2D4A39' }}>
                <strong>Upload a sample statement PDF</strong> from this account. We'll extract the text and auto-detect transaction patterns.
              </p>
            </div>

            <div>
              <Label htmlFor="sample-pdf">Sample PDF Statement</Label>
              <input
                id="sample-pdf"
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
                className="mt-2 block w-full text-sm border border-[#E5E2DC] rounded-lg cursor-pointer p-2"
              />
              {file && (
                <p className="mt-2 text-sm" style={{ color: '#5C745A' }}>
                  Selected: {file.name}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="pdf-pwd">PDF Password (if protected)</Label>
              <Input
                id="pdf-pwd"
                type="text"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password if PDF is protected"
              />
              <p className="text-xs mt-1" style={{ color: '#78716C' }}>
                We'll save this password for future uploads from this account
              </p>
            </div>

            <Button
              onClick={handleFileUpload}
              disabled={!file || loading}
              className="w-full bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
            >
              {loading ? (
                <>Processing...</>
              ) : (
                <>
                  <FileText size={18} className="mr-2" />
                  Analyze PDF
                </>
              )}
            </Button>
          </div>
        )}

        {/* Step 2: Review Results */}
        {step === 2 && (
          <div className="space-y-6">
            <Tabs defaultValue="transactions" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="transactions">
                  Auto-Detected Transactions ({autoTransactions.length})
                </TabsTrigger>
                <TabsTrigger value="text">
                  Extracted Text
                </TabsTrigger>
              </TabsList>

              <TabsContent value="transactions" className="space-y-4">
                {autoTransactions.length > 0 ? (
                  <>
                    <div className="bg-[#E7F3F0] border border-[#5C745A] rounded-lg p-4">
                      <p className="text-sm flex items-center gap-2" style={{ color: '#2D4A39' }}>
                        <Check size={18} />
                        <strong>Success!</strong> Auto-detected {autoTransactions.length} transactions
                        {detectedStrategy && <span className="text-xs opacity-75">(strategy: {detectedStrategy.replace('_', ' ')})</span>}
                      </p>
                      {Object.keys(allStrategies).length > 1 && (
                        <p className="text-xs mt-1 opacity-60">
                          Other strategies tried: {Object.entries(allStrategies).map(([k, v]) => `${k.replace('_', ' ')}: ${v}`).join(', ')}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {autoTransactions.map((txn, idx) => (
                        <div key={idx} className="border border-[#E5E2DC] rounded-lg p-3 hover:bg-[#F9F8F6]">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="text-xs" style={{ color: '#78716C' }}>{txn.date}</div>
                              <div className="font-medium mt-1" style={{ color: '#1C1917' }}>{txn.description}</div>
                            </div>
                            <div className={`text-right font-mono ${txn.type === 'credit' ? 'text-[#5C745A]' : 'text-[#C06B52]'}`}>
                              {txn.type === 'credit' ? '+' : '-'}₹{txn.amount.toFixed(2)}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="flex gap-3">
                      <Button
                        onClick={handleSaveAutoPattern}
                        className="flex-1 bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
                      >
                        <Check size={18} className="mr-2" />
                        Save & Use Auto-Detection
                      </Button>
                      <Button
                        onClick={resetBuilder}
                        className="bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
                      >
                        Try Another PDF
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="bg-[#FEF3C7] border border-[#F59E0B] rounded-lg p-4">
                    <p className="text-sm" style={{ color: '#92400E' }}>
                      <strong>No transactions auto-detected.</strong> The format might be uncommon. Check the extracted text below to understand the format.
                    </p>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="text" className="space-y-4">
                <div className="bg-white border border-[#E5E2DC] rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium" style={{ color: '#1C1917' }}>
                      Extracted Text ({extractedText.length} characters)
                    </span>
                    <Button
                      onClick={() => {
                        navigator.clipboard.writeText(extractedText);
                        toast.success('Text copied to clipboard');
                      }}
                      className="text-xs bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
                    >
                      Copy
                    </Button>
                  </div>
                  <pre className="text-xs bg-[#F9F8F6] p-4 rounded border border-[#E5E2DC] max-h-96 overflow-auto font-mono whitespace-pre-wrap">
                    {extractedText}
                  </pre>
                </div>

                <Button
                  onClick={resetBuilder}
                  className="w-full bg-[#F9F8F6] text-[#1C1917] hover:bg-[#E5E2DC] border border-[#E5E2DC] rounded-lg"
                >
                  Try Another PDF
                </Button>
              </TabsContent>
            </Tabs>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ParserBuilder;
