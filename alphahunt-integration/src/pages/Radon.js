import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, BarChart3, Search, TrendingUp, TrendingDown,
  AlertTriangle, CheckCircle, XCircle, Target, Zap, Eye,
  Plus, Trash2, RefreshCw, ArrowRight
} from 'lucide-react';
import { radonApi } from '../services/radonApi';

// --------------- helpers ---------------

const TABS = [
  { key: 'terminal', label: 'Terminal', icon: Activity },
  { key: 'evaluate', label: 'Evaluate', icon: Target },
  { key: 'scan', label: 'Scan', icon: BarChart3 },
  { key: 'strategies', label: 'Strategies', icon: Zap },
];

function signalColor(signal) {
  if (!signal) return { text: 'text-gray-400', bg: 'bg-gray-500/20' };
  const s = signal.toUpperCase();
  if (s === 'BULLISH' || s === 'LEAN_BULLISH') return { text: 'text-emerald-400', bg: 'bg-emerald-500/20' };
  if (s === 'BEARISH' || s === 'LEAN_BEARISH') return { text: 'text-red-400', bg: 'bg-red-500/20' };
  return { text: 'text-gray-400', bg: 'bg-gray-500/20' };
}

function pcSignal(ratio) {
  if (ratio == null) return 'NEUTRAL';
  if (ratio > 2.0) return 'BEARISH';
  if (ratio > 1.2) return 'LEAN_BEARISH';
  if (ratio > 0.8) return 'NEUTRAL';
  if (ratio > 0.5) return 'LEAN_BULLISH';
  return 'BULLISH';
}

function analystSignal(buyPct) {
  if (buyPct == null) return 'NEUTRAL';
  if (buyPct >= 70) return 'BULLISH';
  if (buyPct >= 50) return 'LEAN_BULLISH';
  if (buyPct >= 30) return 'LEAN_BEARISH';
  return 'BEARISH';
}

// --------------- sub-components ---------------

function StatusDot({ ok }) {
  return (
    <span className={`inline-block w-2.5 h-2.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`} />
  );
}

function SignalBadge({ signal }) {
  const c = signalColor(signal);
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${c.text} ${c.bg}`}>
      {signal || 'N/A'}
    </span>
  );
}

function MilestoneStep({ index, label, status, detail }) {
  const passed = status === 'PASS';
  const failed = status === 'FAIL';
  const pending = !status;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex items-start gap-3 bg-gray-800/40 border border-gray-700/50 rounded-xl p-4"
    >
      <div className="mt-0.5">
        {passed && <CheckCircle size={20} className="text-emerald-400" />}
        {failed && <XCircle size={20} className="text-red-400" />}
        {pending && <AlertTriangle size={20} className="text-gray-500" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white">
          {index + 1}. {label}
        </p>
        {detail && (
          <p className={`text-xs mt-1 ${passed ? 'text-emerald-400' : failed ? 'text-red-400' : 'text-gray-400'}`}>
            {detail}
          </p>
        )}
      </div>
      <span className={`text-xs font-mono font-bold ${passed ? 'text-emerald-400' : failed ? 'text-red-400' : 'text-gray-500'}`}>
        {status || '---'}
      </span>
    </motion.div>
  );
}

// --------------- tab: Terminal ---------------

function TerminalTab() {
  const [apiOk, setApiOk] = useState(null);
  const [brokerOk, setBrokerOk] = useState(null);
  const [ticker, setTicker] = useState('');
  const [tickerResult, setTickerResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const checkStatus = useCallback(async () => {
    const h = await radonApi.health();
    setApiOk(!h.error);
    const b = await radonApi.getBrokerStatus();
    setBrokerOk(!b.error && b.connected !== false);
  }, []);

  useEffect(() => { checkStatus(); }, [checkStatus]);

  const lookupTicker = async () => {
    if (!ticker.trim()) return;
    setLoading(true);
    setTickerResult(null);
    const res = await radonApi.getTicker(ticker.trim().toUpperCase());
    setTickerResult(res);
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Status Panel */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">System Status</h3>
          <button
            onClick={checkStatus}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700/50 rounded-lg transition"
          >
            <RefreshCw size={16} />
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <StatusDot ok={apiOk} />
            <div>
              <p className="text-sm font-medium text-white">FastAPI Backend</p>
              <p className={`text-xs ${apiOk ? 'text-emerald-400' : apiOk === false ? 'text-red-400' : 'text-gray-400'}`}>
                {apiOk ? 'Connected' : apiOk === false ? 'Disconnected' : 'Checking...'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusDot ok={brokerOk} />
            <div>
              <p className="text-sm font-medium text-white">Alpaca Broker</p>
              <p className={`text-xs ${brokerOk ? 'text-emerald-400' : brokerOk === false ? 'text-red-400' : 'text-gray-400'}`}>
                {brokerOk ? 'Connected' : brokerOk === false ? 'Disconnected' : 'Checking...'}
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Quick Ticker Lookup */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">Quick Ticker Lookup</h3>
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && lookupTicker()}
              placeholder="Enter ticker symbol..."
              className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition"
            />
          </div>
          <button
            onClick={lookupTicker}
            disabled={loading || !ticker.trim()}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition"
          >
            {loading ? <RefreshCw size={16} className="animate-spin" /> : <ArrowRight size={16} />}
          </button>
        </div>

        {tickerResult && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4"
          >
            {tickerResult.error ? (
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <XCircle size={16} />
                <span>{tickerResult.error}</span>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Symbol</p>
                  <p className="text-lg font-bold text-white font-mono">{tickerResult.ticker || tickerResult.symbol}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Name</p>
                  <p className="text-sm font-medium text-white truncate">{tickerResult.name || tickerResult.shortName || '---'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Price</p>
                  <p className="text-lg font-bold text-white font-mono">
                    {tickerResult.price != null ? `$${Number(tickerResult.price).toFixed(2)}` : '---'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Sector</p>
                  <p className="text-sm font-medium text-gray-300">{tickerResult.sector || '---'}</p>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

// --------------- tab: Evaluate ---------------

function EvaluateTab() {
  const [ticker, setTicker] = useState('');
  const [bankroll, setBankroll] = useState('10000');
  const [milestones, setMilestones] = useState([]);
  const [running, setRunning] = useState(false);

  const MILESTONE_LABELS = [
    'Ticker Validation',
    'Analyst Ratings',
    'Options Flow',
    'Institutional Signals',
    'Edge Decision',
    'Structure Suggestion',
    'Kelly Sizing',
  ];

  const runEvaluation = async () => {
    const sym = ticker.trim().toUpperCase();
    if (!sym) return;
    setRunning(true);
    setMilestones([]);
    const steps = [];

    // 1 - Validate ticker
    const tickerRes = await radonApi.getTicker(sym);
    if (tickerRes.error) {
      steps.push({ label: MILESTONE_LABELS[0], status: 'FAIL', detail: tickerRes.error });
      setMilestones([...steps]);
      setRunning(false);
      return;
    }
    steps.push({ label: MILESTONE_LABELS[0], status: 'PASS', detail: `${tickerRes.name || sym} validated` });
    setMilestones([...steps]);

    // 2 - Analyst ratings
    const analystRes = await radonApi.getAnalyst(sym);
    const buyPct = analystRes.buy_percent ?? analystRes.buyPercent;
    const aSignal = analystSignal(buyPct);
    steps.push({
      label: MILESTONE_LABELS[1],
      status: 'PASS',
      detail: analystRes.error
        ? `Could not fetch: ${analystRes.error}`
        : `Buy ${buyPct != null ? buyPct + '%' : 'N/A'} - ${aSignal}`,
    });
    setMilestones([...steps]);

    // 3 - Options flow
    const flowRes = await radonApi.getFlow(sym);
    const pcRatio = flowRes.put_call_ratio ?? flowRes.putCallRatio;
    const iv = flowRes.atm_iv ?? flowRes.atmIV ?? flowRes.iv;
    const pSignal = pcSignal(pcRatio);
    steps.push({
      label: MILESTONE_LABELS[2],
      status: 'PASS',
      detail: flowRes.error
        ? `Could not fetch: ${flowRes.error}`
        : `P/C ${pcRatio != null ? Number(pcRatio).toFixed(2) : 'N/A'} (${pSignal}) | IV ${iv != null ? (Number(iv) * 100).toFixed(1) + '%' : 'N/A'}`,
    });
    setMilestones([...steps]);

    // 4 - Institutional signals
    const shortInterest = flowRes.short_interest ?? flowRes.shortInterest;
    steps.push({
      label: MILESTONE_LABELS[3],
      status: 'PASS',
      detail: `Short Interest: ${shortInterest != null ? (Number(shortInterest) * 100).toFixed(1) + '%' : 'N/A'}`,
    });
    setMilestones([...steps]);

    // 5 - Edge decision
    const signals = [pSignal, aSignal].filter((s) => s !== 'NEUTRAL');
    const hasBullish = signals.some((s) => s.includes('BULLISH'));
    const hasBearish = signals.some((s) => s.includes('BEARISH') && !s.includes('LEAN_BULLISH'));
    const edgePass = signals.length >= 1 && !(hasBullish && hasBearish);
    steps.push({
      label: MILESTONE_LABELS[4],
      status: edgePass ? 'PASS' : 'FAIL',
      detail: edgePass
        ? `${signals.length} confirming signal(s) detected`
        : 'Conflicting or no signals - no edge',
    });
    setMilestones([...steps]);

    if (!edgePass) {
      steps.push({ label: MILESTONE_LABELS[5], status: 'FAIL', detail: 'Skipped - no edge' });
      steps.push({ label: MILESTONE_LABELS[6], status: 'FAIL', detail: 'Skipped - no edge' });
      setMilestones([...steps]);
      setRunning(false);
      return;
    }

    // 6 - Structure suggestion
    const direction = hasBullish ? 'BULLISH' : 'BEARISH';
    steps.push({
      label: MILESTONE_LABELS[5],
      status: 'PASS',
      detail: direction === 'BULLISH'
        ? 'Suggested: Bull call vertical (defined risk, R:R > 2:1)'
        : 'Suggested: Bear put vertical (defined risk, R:R > 2:1)',
    });
    setMilestones([...steps]);

    // 7 - Kelly sizing
    const br = parseFloat(bankroll) || 10000;
    const kellyRes = await radonApi.calculateKelly({
      ticker: sym,
      bankroll: br,
      win_prob: 0.55,
      win_loss_ratio: 2.5,
    });
    const maxPosition = Math.min(br * 0.025, br);
    const posSize = kellyRes.position_size ?? kellyRes.positionSize ?? maxPosition;
    steps.push({
      label: MILESTONE_LABELS[6],
      status: 'PASS',
      detail: `Position size: $${Number(posSize).toFixed(0)} (max 2.5% of $${br.toLocaleString()})`,
    });
    setMilestones([...steps]);
    setRunning(false);
  };

  return (
    <div className="space-y-6">
      {/* Input */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">7-Milestone Evaluation</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="text-xs text-gray-500 mb-1 block">Ticker</label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition font-mono"
            />
          </div>
          <div className="sm:col-span-1">
            <label className="text-xs text-gray-500 mb-1 block">Bankroll ($)</label>
            <input
              type="number"
              value={bankroll}
              onChange={(e) => setBankroll(e.target.value)}
              placeholder="10000"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition font-mono"
            />
          </div>
          <div className="sm:col-span-1 flex items-end">
            <button
              onClick={runEvaluation}
              disabled={running || !ticker.trim()}
              className="w-full px-4 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
            >
              {running ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Target size={16} />
                  Evaluate
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Milestones */}
      {milestones.length > 0 && (
        <div className="space-y-3">
          {milestones.map((m, i) => (
            <MilestoneStep
              key={i}
              index={i}
              label={m.label}
              status={m.status}
              detail={m.detail}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --------------- tab: Scan ---------------

function ScanTab() {
  const [input, setInput] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [watchlist, setWatchlist] = useState([]);
  const [newWl, setNewWl] = useState('');

  const fetchWatchlist = useCallback(async () => {
    const res = await radonApi.getWatchlist();
    if (!res.error && Array.isArray(res.tickers || res)) {
      setWatchlist(res.tickers || res);
    }
  }, []);

  useEffect(() => { fetchWatchlist(); }, [fetchWatchlist]);

  const addWl = async () => {
    const sym = newWl.trim().toUpperCase();
    if (!sym) return;
    await radonApi.addToWatchlist(sym);
    setNewWl('');
    fetchWatchlist();
  };

  const removeWl = async (sym) => {
    await radonApi.removeFromWatchlist(sym);
    fetchWatchlist();
  };

  const runScan = async (tickers) => {
    setLoading(true);
    setResults([]);
    const res = await radonApi.runScan(tickers);
    if (res.error) {
      setResults([]);
    } else {
      const list = Array.isArray(res) ? res : res.results || [];
      list.sort((a, b) => (b.signal_count ?? b.signalCount ?? 0) - (a.signal_count ?? a.signalCount ?? 0));
      setResults(list);
    }
    setLoading(false);
  };

  const scanCustom = () => {
    const tickers = input
      .split(',')
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    if (tickers.length) runScan(tickers);
  };

  return (
    <div className="space-y-6">
      {/* Watchlist */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Eye size={18} /> Watchlist
          </h3>
          <button
            onClick={() => runScan(watchlist)}
            disabled={loading || watchlist.length === 0}
            className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition flex items-center gap-1"
          >
            <BarChart3 size={14} /> Scan Watchlist
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          {watchlist.length === 0 && (
            <p className="text-sm text-gray-500">No tickers in watchlist</p>
          )}
          {watchlist.map((sym) => (
            <span
              key={sym}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-gray-700/50 border border-gray-600/50 rounded-full text-sm text-white font-mono"
            >
              {sym}
              <button onClick={() => removeWl(sym)} className="text-gray-400 hover:text-red-400 transition">
                <Trash2 size={12} />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newWl}
            onChange={(e) => setNewWl(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && addWl()}
            placeholder="Add ticker..."
            className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition text-sm font-mono"
          />
          <button
            onClick={addWl}
            disabled={!newWl.trim()}
            className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition"
          >
            <Plus size={16} />
          </button>
        </div>
      </motion.div>

      {/* Custom Scan */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6"
      >
        <h3 className="text-lg font-semibold text-white mb-4">Custom Scan</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && scanCustom()}
            placeholder="AAPL, MSFT, TSLA..."
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition font-mono"
          />
          <button
            onClick={scanCustom}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition flex items-center gap-2"
          >
            {loading ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
            Scan
          </button>
        </div>
      </motion.div>

      {/* Results */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800/40 border border-gray-700/50 rounded-xl overflow-hidden"
        >
          <div className="p-4 sm:p-6 border-b border-gray-700/50">
            <h3 className="text-lg font-semibold text-white">Scan Results</h3>
          </div>
          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-gray-700/50">
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Ticker</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">P/C Ratio</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Signal</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">ATM IV</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium">Short Interest</th>
                  <th className="px-4 py-3 text-xs text-gray-500 font-medium"># Signals</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => {
                  const ratio = r.put_call_ratio ?? r.putCallRatio;
                  const sig = pcSignal(ratio);
                  const iv = r.atm_iv ?? r.atmIV ?? r.iv;
                  const si = r.short_interest ?? r.shortInterest;
                  const sc = r.signal_count ?? r.signalCount ?? 0;
                  return (
                    <motion.tr
                      key={r.ticker || r.symbol || i}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="border-b border-gray-700/30 hover:bg-gray-700/20 transition"
                    >
                      <td className="px-4 py-3 text-white font-mono font-bold">{r.ticker || r.symbol}</td>
                      <td className="px-4 py-3 text-white font-mono">{ratio != null ? Number(ratio).toFixed(2) : '---'}</td>
                      <td className="px-4 py-3"><SignalBadge signal={sig} /></td>
                      <td className="px-4 py-3 text-white font-mono">{iv != null ? (Number(iv) * 100).toFixed(1) + '%' : '---'}</td>
                      <td className="px-4 py-3 text-white font-mono">{si != null ? (Number(si) * 100).toFixed(1) + '%' : '---'}</td>
                      <td className="px-4 py-3 text-white font-mono font-bold">{sc}</td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {/* Mobile cards */}
          <div className="sm:hidden divide-y divide-gray-700/30">
            {results.map((r, i) => {
              const ratio = r.put_call_ratio ?? r.putCallRatio;
              const sig = pcSignal(ratio);
              const iv = r.atm_iv ?? r.atmIV ?? r.iv;
              const si = r.short_interest ?? r.shortInterest;
              const sc = r.signal_count ?? r.signalCount ?? 0;
              return (
                <motion.div
                  key={r.ticker || r.symbol || i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-white font-mono font-bold">{r.ticker || r.symbol}</span>
                    <SignalBadge signal={sig} />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <p className="text-xs text-gray-500">P/C Ratio</p>
                      <p className="text-sm font-mono text-white">{ratio != null ? Number(ratio).toFixed(2) : '---'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">ATM IV</p>
                      <p className="text-sm font-mono text-white">{iv != null ? (Number(iv) * 100).toFixed(1) + '%' : '---'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500"># Signals</p>
                      <p className="text-sm font-mono font-bold text-white">{sc}</p>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}
    </div>
  );
}

// --------------- tab: Strategies ---------------

const STRATEGIES = [
  {
    key: 'leap',
    title: 'LEAP IV Mispricing',
    description: 'Scan for long-dated options where implied volatility significantly diverges from historical realized vol, indicating potential mispricing opportunities.',
    icon: TrendingUp,
    endpoint: 'leap-scan',
  },
  {
    key: 'garch',
    title: 'GARCH Convergence',
    description: 'Cross-asset GARCH volatility divergence analysis. Identifies pairs where volatility regimes are diverging and likely to converge.',
    icon: Activity,
    endpoint: 'garch-convergence',
  },
  {
    key: 'vcg',
    title: 'VCG Scan',
    description: 'Volatility-credit gap divergence scanner. Detects when options implied vol and credit spreads send conflicting signals about risk.',
    icon: BarChart3,
    endpoint: 'vcg-scan',
  },
];

function StrategiesTab() {
  const [runningKey, setRunningKey] = useState(null);
  const [stratResults, setStratResults] = useState({});

  const runStrategy = async (strat) => {
    setRunningKey(strat.key);
    const res = await radonApi.runScan([strat.endpoint]);
    setStratResults((prev) => ({ ...prev, [strat.key]: res }));
    setRunningKey(null);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {STRATEGIES.map((strat, i) => {
        const Icon = strat.icon;
        const result = stratResults[strat.key];
        return (
          <motion.div
            key={strat.key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4 sm:p-6 flex flex-col"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
                <Icon size={20} className="text-emerald-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">{strat.title}</h3>
            </div>
            <p className="text-sm text-gray-400 mb-4 flex-1">{strat.description}</p>
            <button
              onClick={() => runStrategy(strat)}
              disabled={runningKey === strat.key}
              className="w-full px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
            >
              {runningKey === strat.key ? (
                <>
                  <RefreshCw size={16} className="animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Zap size={16} />
                  Run
                </>
              )}
            </button>
            {result && (
              <div className="mt-3 p-3 bg-gray-900/50 rounded-lg">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap break-words max-h-40 overflow-y-auto font-mono">
                  {result.error ? result.error : JSON.stringify(result, null, 2)}
                </pre>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

// --------------- main page ---------------

const Radon = () => {
  const [activeTab, setActiveTab] = useState('terminal');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-blue-600 rounded-lg flex items-center justify-center">
            <Activity size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white">Radon Terminal</h1>
            <p className="text-sm text-gray-400">Convexity-first options analysis</p>
          </div>
        </div>
      </motion.div>

      {/* Tab Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="flex gap-1 mb-6 bg-gray-800/40 border border-gray-700/50 rounded-xl p-1 overflow-x-auto"
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                active
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700/30'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </motion.div>

      {/* Tab Content */}
      {activeTab === 'terminal' && <TerminalTab />}
      {activeTab === 'evaluate' && <EvaluateTab />}
      {activeTab === 'scan' && <ScanTab />}
      {activeTab === 'strategies' && <StrategiesTab />}
    </div>
  );
};

export default Radon;
