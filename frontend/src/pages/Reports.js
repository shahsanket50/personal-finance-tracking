import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { ChartLine, TrendUp, TrendDown, Scales, ArrowsDownUp, CurrencyCircleDollar, Printer } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

const Reports = () => {
  const [activeReport, setActiveReport] = useState('pl');
  const [plData, setPlData] = useState(null);
  const [bsData, setBsData] = useState(null);
  const [cfData, setCfData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [asOfDate, setAsOfDate] = useState('');
  const [fyYears, setFyYears] = useState([]);
  const [selectedFy, setSelectedFy] = useState('');

  useEffect(() => {
    axios.get(`${API}/financial-years`).then(res => {
      const years = res.data.years || [];
      setFyYears(years);
      if (years.length > 0) {
        const current = years.find(y => y.label === res.data.current_fy) || years[0];
        setSelectedFy(current.label);
        setStartDate(current.start);
        setEndDate(current.end);
        setAsOfDate(current.end);
        // Load initial report with FY dates directly (state not yet updated)
        loadReportWithDates(current.start, current.end, current.end);
      } else {
        loadReportWithDates('', '', '');
      }
    }).catch(() => {
      loadReportWithDates('', '', '');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (startDate || endDate || asOfDate) loadReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeReport]);

  const onFyChange = (fyLabel) => {
    setSelectedFy(fyLabel);
    const fy = fyYears.find(y => y.label === fyLabel);
    if (fy) {
      setStartDate(fy.start);
      setEndDate(fy.end);
      setAsOfDate(fy.end);
    }
  };

  const loadReportWithDates = async (sd, ed, aod) => {
    setLoading(true);
    try {
      if (activeReport === 'pl') {
        let url = `${API}/profit-loss`;
        const params = [];
        if (sd) params.push(`start_date=${sd}`);
        if (ed) params.push(`end_date=${ed}`);
        if (params.length) url += '?' + params.join('&');
        const res = await axios.get(url);
        setPlData(res.data);
      } else if (activeReport === 'bs') {
        let url = `${API}/balance-sheet`;
        if (aod) url += `?as_of_date=${aod}`;
        const res = await axios.get(url);
        setBsData(res.data);
      } else {
        let url = `${API}/cash-flow`;
        const params = [];
        if (sd) params.push(`start_date=${sd}`);
        if (ed) params.push(`end_date=${ed}`);
        if (params.length) url += '?' + params.join('&');
        const res = await axios.get(url);
        setCfData(res.data);
      }
    } catch {
      toast.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const loadReport = async () => {
    await loadReportWithDates(startDate, endDate, asOfDate);
  };

  const handlePrint = () => {
    window.print();
  };

  // Group items by group_name for Tally-style subtotals
  const groupByGroupName = (items) => {
    const grouped = {};
    items.forEach(item => {
      const g = item.group_name || 'Other';
      if (!grouped[g]) grouped[g] = [];
      grouped[g].push(item);
    });
    return Object.entries(grouped).map(([name, rows]) => ({
      name,
      rows,
      total: rows.reduce((s, r) => s + r.amount, 0)
    }));
  };

  const renderGroupedTable = (items, total, colorPositive, colorNegative, label) => {
    const groups = groupByGroupName(items);
    if (items.length === 0) return <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No {label.toLowerCase()} entries</p>;
    return (
      <table className="w-full text-sm">
        <tbody>
          {groups.map((group) => (
            <React.Fragment key={group.name}>
              <tr style={{ background: 'var(--app-bg)' }}>
                <td colSpan={2} className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--app-text-muted)' }}>
                  {group.name}
                </td>
              </tr>
              {group.rows.map((item, i) => (
                <tr key={i} className="border-t" style={{ borderColor: 'var(--app-border)' }}>
                  <td className="px-4 py-2 pl-8" style={{ color: 'var(--app-text)' }}>{item.ledger_name}</td>
                  <td className="px-4 py-2 text-right font-mono" style={{ color: item.amount >= 0 ? colorPositive : colorNegative }}>
                    {item.amount.toLocaleString('en-IN')}
                  </td>
                </tr>
              ))}
              {groups.length > 1 && (
                <tr className="border-t" style={{ borderColor: 'var(--app-border)', background: 'var(--app-bg)' }}>
                  <td className="px-4 py-1.5 pl-8 text-xs font-medium italic" style={{ color: 'var(--app-text-muted)' }}>Subtotal</td>
                  <td className="px-4 py-1.5 text-right font-mono text-xs font-medium" style={{ color: group.total >= 0 ? colorPositive : colorNegative }}>
                    {group.total.toLocaleString('en-IN')}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 font-bold" style={{ borderColor: colorPositive }}>
            <td className="px-4 py-2.5" style={{ color: colorPositive }}>Total {label}</td>
            <td className="px-4 py-2.5 text-right font-mono" style={{ color: colorPositive }}>{total.toLocaleString('en-IN')}</td>
          </tr>
        </tfoot>
      </table>
    );
  };

  const renderPL = () => {
    if (!plData) return null;
    return (
      <div className="space-y-4" data-testid="pl-report">
        <div className="grid grid-cols-3 gap-4">
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <TrendUp size={18} style={{ color: '#5C745A' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Income</span>
            </div>
            <p className="text-xl font-bold" style={{ color: '#5C745A' }} data-testid="pl-total-income">{plData.total_income.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <TrendDown size={18} style={{ color: '#C06B52' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Expenses</span>
            </div>
            <p className="text-xl font-bold" style={{ color: '#C06B52' }} data-testid="pl-total-expenses">{plData.total_expenses.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="flex items-center gap-2 mb-1">
              <Scales size={18} style={{ color: plData.net_profit >= 0 ? '#5C745A' : '#C06B52' }} />
              <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Net {plData.net_profit >= 0 ? 'Profit' : 'Loss'}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: plData.net_profit >= 0 ? '#5C745A' : '#C06B52' }} data-testid="pl-net-profit">
              {plData.net_profit.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#5C745A08' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#5C745A' }}>Income</h3>
            </div>
            {renderGroupedTable(plData.income, plData.total_income, '#5C745A', '#C06B52', 'Income')}
          </div>

          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#C06B5208' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#C06B52' }}>Expenses</h3>
            </div>
            {renderGroupedTable(plData.expenses, plData.total_expenses, '#C06B52', '#5C745A', 'Expenses')}
          </div>
        </div>
      </div>
    );
  };

  const renderBS = () => {
    if (!bsData) return null;
    return (
      <div className="space-y-4" data-testid="bs-report">
        <div className="grid grid-cols-3 gap-4">
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Assets</span>
            <p className="text-xl font-bold" style={{ color: '#5C745A' }} data-testid="bs-total-assets">{bsData.total_assets.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Total Liabilities</span>
            <p className="text-xl font-bold" style={{ color: '#C06B52' }} data-testid="bs-total-liabilities">{bsData.total_liabilities.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Status</span>
            <p className="text-xl font-bold" style={{ color: bsData.is_balanced ? '#5C745A' : '#C06B52' }} data-testid="bs-status">
              {bsData.is_balanced ? 'Balanced' : 'Unbalanced'}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#5C745A08' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#5C745A' }}>Assets</h3>
            </div>
            {renderGroupedTable(bsData.assets, bsData.total_assets, '#5C745A', '#C06B52', 'Assets')}
          </div>

          <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--app-border)', background: '#C06B5208' }}>
              <h3 className="font-semibold text-sm" style={{ color: '#C06B52' }}>Liabilities & Capital</h3>
            </div>
            {renderGroupedTable(bsData.liabilities, bsData.total_liabilities, '#C06B52', '#5C745A', 'Liabilities')}
          </div>
        </div>
      </div>
    );
  };

  const renderCF = () => {
    if (!cfData) return null;

    const renderSection = (title, data, icon, color) => (
      <div className="border rounded-lg overflow-hidden" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
        <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: 'var(--app-border)', background: `${color}08` }}>
          <h3 className="font-semibold text-sm flex items-center gap-2" style={{ color }}>
            {icon} {title}
          </h3>
          <span className="font-mono font-bold text-sm" style={{ color }}>{data.total.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</span>
        </div>
        {data.items.length === 0 ? (
          <p className="p-4 text-sm" style={{ color: 'var(--app-text-muted)' }}>No activity</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {data.items.map((item, i) => (
                <tr key={i} className={i > 0 ? 'border-t' : ''} style={{ borderColor: 'var(--app-border)' }}>
                  <td className="px-4 py-2" style={{ color: 'var(--app-text)' }}>
                    {item.ledger_name}
                    <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--app-bg)', color: 'var(--app-text-muted)' }}>{item.group_name}</span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono" style={{ color: item.amount >= 0 ? '#5C745A' : '#C06B52' }}>
                    {item.amount >= 0 ? '+' : ''}{item.amount.toLocaleString('en-IN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    );

    return (
      <div className="space-y-4" data-testid="cf-report">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Opening Cash</span>
            <p className="text-lg font-bold font-mono" style={{ color: 'var(--app-text)' }} data-testid="cf-opening-cash">{cfData.opening_cash.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Net Change</span>
            <p className="text-lg font-bold font-mono" style={{ color: cfData.net_cash_change >= 0 ? '#5C745A' : '#C06B52' }} data-testid="cf-net-change">
              {cfData.net_cash_change >= 0 ? '+' : ''}{cfData.net_cash_change.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}
            </p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Closing Cash</span>
            <p className="text-lg font-bold font-mono" style={{ color: cfData.closing_cash >= 0 ? '#5C745A' : '#C06B52' }} data-testid="cf-closing-cash">{cfData.closing_cash.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</p>
          </div>
          <div className="border rounded-lg p-4" style={{ background: 'var(--app-surface)', borderColor: 'var(--app-border)' }}>
            <span className="text-xs" style={{ color: 'var(--app-text-muted)' }}>Period</span>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--app-text)' }}>{selectedFy || 'All Time'}</p>
          </div>
        </div>

        {renderSection('Operating Activities', cfData.operating, <ArrowsDownUp size={16} />, '#5C745A')}
        {renderSection('Investing Activities', cfData.investing, <CurrencyCircleDollar size={16} />, '#7CA1A6')}
        {renderSection('Financing Activities', cfData.financing, <CurrencyCircleDollar size={16} />, '#D4A373')}
      </div>
    );
  };

  const tabs = [
    { id: 'pl', label: 'Profit & Loss', icon: <ChartLine size={16} className="inline mr-1.5" /> },
    { id: 'bs', label: 'Balance Sheet', icon: <Scales size={16} className="inline mr-1.5" /> },
    { id: 'cf', label: 'Cash Flow', icon: <ArrowsDownUp size={16} className="inline mr-1.5" /> },
  ];

  return (
    <div className="space-y-4" data-testid="reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--app-text)' }}>Financial Reports</h1>
          {selectedFy && <p className="text-sm" style={{ color: 'var(--app-text-muted)' }}>{selectedFy}</p>}
        </div>
        <button
          onClick={handlePrint}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors border print:hidden"
          style={{ borderColor: 'var(--app-border)', color: 'var(--app-text-muted)', background: 'var(--app-surface)' }}
          data-testid="print-report-btn"
        >
          <Printer size={16} /> Print
        </button>
      </div>

      {/* Report Tabs */}
      <div className="flex gap-2 print:hidden">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveReport(tab.id)}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: activeReport === tab.id ? 'var(--app-accent)' : 'var(--app-surface)',
              color: activeReport === tab.id ? 'white' : 'var(--app-text-muted)',
              border: `1px solid ${activeReport === tab.id ? 'var(--app-accent)' : 'var(--app-border)'}`,
            }}
            data-testid={`tab-${tab.id}`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Date Filters */}
      <div className="flex flex-wrap gap-3 items-end print:hidden">
        {fyYears.length > 0 && (
          <div>
            <Label className="text-xs">Financial Year</Label>
            <select
              value={selectedFy}
              onChange={e => onFyChange(e.target.value)}
              className="flex h-9 w-44 rounded-md border px-3 py-1 text-sm"
              style={{ borderColor: 'var(--app-border)', background: 'var(--app-surface)', color: 'var(--app-text)' }}
              data-testid="fy-selector"
            >
              {fyYears.map(fy => (
                <option key={fy.label} value={fy.label}>{fy.label}</option>
              ))}
            </select>
          </div>
        )}
        {activeReport !== 'bs' ? (
          <>
            <div>
              <Label className="text-xs">From</Label>
              <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-40" data-testid="report-start-date" />
            </div>
            <div>
              <Label className="text-xs">To</Label>
              <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-40" data-testid="report-end-date" />
            </div>
          </>
        ) : (
          <div>
            <Label className="text-xs">As of Date</Label>
            <Input type="date" value={asOfDate} onChange={e => setAsOfDate(e.target.value)} className="w-40" data-testid="report-as-of-date" />
          </div>
        )}
        <button onClick={loadReport} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: 'var(--app-accent)' }} data-testid="report-filter-btn">
          Apply
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--app-accent)', borderTopColor: 'transparent' }} />
        </div>
      ) : (
        activeReport === 'pl' ? renderPL() : activeReport === 'bs' ? renderBS() : renderCF()
      )}
    </div>
  );
};

export default Reports;
