import { useState, useEffect } from 'react';
import {
  FlaskConical, TrendingUp, BarChart3, AlertTriangle, WifiOff,
  Loader2, X, Sparkles, CheckCircle2, ShieldAlert, History, Clock
} from 'lucide-react';
import { injectAnomaly, simulateInactivity } from '../api/client';

export default function DemoControls({ 
  isOpen, 
  onClose, 
  currentUserId = 'trader_1',
  watchlistSymbols = []
}) {
  const [loading, setLoading] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [inactivityLoading, setInactivityLoading] = useState(false);
  const [appliedActionId, setAppliedActionId] = useState(null);
  const [appliedTimeMinutes, setAppliedTimeMinutes] = useState(null);

  const fallbackSymbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'TATAMOTORS', 'SBIN', 'BAJFINANCE'];
  const symbols = watchlistSymbols.length > 0 ? watchlistSymbols : fallbackSymbols;

  const [selectedSymbol, setSelectedSymbol] = useState(symbols[0] || 'RELIANCE');

  // Reset feedback state and ensure selectedSymbol is valid whenever user or modal state changes
  useEffect(() => {
    setLastResult(null);
    setAppliedActionId(null);
    setAppliedTimeMinutes(null);
    if (!symbols.includes(selectedSymbol)) {
      setSelectedSymbol(symbols[0] || 'RELIANCE');
    }
  }, [currentUserId, isOpen]);

  // Keep selectedSymbol synced when symbols list updates
  useEffect(() => {
    if (!symbols.includes(selectedSymbol)) {
      setSelectedSymbol(symbols[0] || 'RELIANCE');
    }
  }, [watchlistSymbols]);

  const timeOptions = [
    { label: '15 Mins', minutes: 15, desc: 'Micro drift (tight σ)' },
    { label: '2 Hours', minutes: 120, desc: 'Mid-session (σ√t scaled)' },
    { label: '1 Day', minutes: 1440, desc: 'Full trading day (1.0σ baseline)' },
    { label: '3 Days', minutes: 4320, desc: 'Multi-day absence (wide σ cone)' },
  ];

  const actions = [
    {
      id: 'price_surge',
      label: 'Price Breakout',
      desc: '+6.0% surge (Triggers >2.0σ statistical breakout)',
      icon: TrendingUp,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
    },
    {
      id: 'volume_explosion',
      label: 'Volume Surge',
      desc: '4.0x surge vs 30-day session rolling average',
      icon: BarChart3,
      color: 'text-sky-400',
      bgColor: 'bg-sky-500/10',
      borderColor: 'border-sky-500/20',
    },
    {
      id: 'bad_tick',
      label: 'Bad-Tick Anomaly',
      desc: '+20% anomaly without market depth (Tagged UNVERIFIED_DATA)',
      icon: AlertTriangle,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
    },
    {
      id: 'trading_halt',
      label: 'Exchange Circuit Limit',
      desc: 'Simulate upper/lower band hit (30s cooling pause, auto-resumes)',
      icon: ShieldAlert,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
    },
    {
      id: 'feed_delay',
      label: 'Feed Disruption',
      desc: 'Simulate 10s upstream packet loss / stale feed',
      icon: WifiOff,
      color: 'text-rose-400',
      bgColor: 'bg-rose-500/10',
      borderColor: 'border-rose-500/20',
    },
  ];

  const handleInject = async (actionId) => {
    setLoading(actionId);
    setLastResult(null);
    try {
      const duration = actionId === 'feed_delay' ? 10 : null;
      const result = await injectAnomaly(selectedSymbol, actionId, duration);
      setLastResult({ success: true, message: result.message, action: actionId, symbol: selectedSymbol });
      setAppliedActionId(actionId);
      setTimeout(() => setAppliedActionId(null), 4000);
    } catch (err) {
      setLastResult({ success: false, message: err.response?.data?.detail || err.message });
    }
    setLoading(null);
  };

  const handleSimulateInactivity = async (minutes) => {
    setInactivityLoading(true);
    setLastResult(null);
    try {
      const res = await simulateInactivity(currentUserId, minutes);
      setLastResult({ success: true, message: res.message, minutes });
      setAppliedTimeMinutes(minutes);
      setTimeout(() => setAppliedTimeMinutes(null), 4000);
    } catch (err) {
      setLastResult({ success: false, message: err.response?.data?.detail || err.message });
    }
    setInactivityLoading(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div 
        className="w-full max-w-lg bg-surface-800 border border-themeborder-subtle rounded-2xl shadow-2xl overflow-hidden animate-slide-up flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-themeborder-subtle bg-surface-850">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent-yellow/10 border border-accent-yellow/20 flex items-center justify-center text-accent-yellow">
              <FlaskConical className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-text-primary">Evaluator Sandbox</h2>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-accent-yellow/10 text-accent-yellow border border-accent-yellow/20">
                  Live Test
                </span>
              </div>
              <p className="text-xs text-text-muted">Inject deterministic anomalies & test mathematical time scaling</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Pinned Feedback Alert (Always Visible on Top) */}
        {lastResult && (
          <div className={`px-6 py-3 text-xs flex items-center justify-between border-b animate-slide-down ${
            lastResult.success
              ? 'bg-accent-green/15 text-accent-green border-accent-green/30 font-medium'
              : 'bg-accent-red/15 text-accent-red border-accent-red/30 font-medium'
          }`}>
            <div className="flex items-center gap-2.5">
              {lastResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-accent-green flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-accent-red flex-shrink-0" />
              )}
              <span>{lastResult.message}</span>
            </div>
            <button 
              onClick={() => setLastResult(null)} 
              className="text-text-muted hover:text-text-primary text-[11px] ml-2 p-1"
              title="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[65vh] overflow-y-auto">
          {/* Section 1: Time Machine Simulator */}
          <div className="p-4 rounded-xl bg-surface-850 border border-themeborder-subtle space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-accent-blue" />
                <span className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Time Machine (User Inactivity)
                </span>
              </div>
              <span className="text-[11px] text-text-muted">Scales σ√Δt</span>
            </div>
            <p className="text-[11px] text-text-muted">
              Rewind <span className="font-semibold text-text-primary">{currentUserId}</span>'s checkpoint to see how the mathematical volatility window scales over time:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {timeOptions.map((t) => {
                const isApplied = appliedTimeMinutes === t.minutes;
                return (
                  <button
                    key={t.minutes}
                    onClick={() => handleSimulateInactivity(t.minutes)}
                    disabled={inactivityLoading}
                    className={`p-2.5 rounded-xl border transition-all text-center group disabled:opacity-50 relative ${
                      isApplied 
                        ? 'bg-accent-blue/20 border-accent-blue text-accent-blue ring-2 ring-accent-blue/30' 
                        : 'bg-surface-700 hover:bg-accent-blue/15 hover:border-accent-blue/30 border-themeborder-subtle'
                    }`}
                  >
                    <div className="text-xs font-bold text-text-primary group-hover:text-accent-blue flex items-center justify-center gap-1">
                      {t.label}
                      {isApplied && <CheckCircle2 className="w-3 h-3 text-accent-blue" />}
                    </div>
                    <div className="text-[9px] text-text-muted truncate mt-0.5">{t.desc.split(' ')[0]}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Target Symbol Picker */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                Target Instrument
              </label>
              <span className="text-[11px] text-accent-green font-medium">
                {watchlistSymbols.length > 0 ? `${symbols.length} stocks in ${currentUserId}'s watchlist` : 'Default universe'}
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {symbols.map(s => (
                <button
                  key={s}
                  onClick={() => setSelectedSymbol(s)}
                  className={`py-1.5 px-3 text-center rounded-xl text-xs font-semibold transition-all ${
                    selectedSymbol === s
                      ? 'bg-accent-green text-surface-950 shadow-md shadow-accent-green/20'
                      : 'bg-surface-700 text-text-secondary hover:bg-surface-600 hover:text-text-primary border border-themeborder-subtle'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Action List */}
          <div className="space-y-2.5">
            <label className="text-xs font-semibold text-text-muted block uppercase tracking-wider">
              Select Market Anomaly Scenario
            </label>
            {actions.map(action => {
              const Icon = action.icon;
              const isLoading = loading === action.id;
              const isApplied = appliedActionId === action.id;

              return (
                <button
                  key={action.id}
                  onClick={() => handleInject(action.id)}
                  disabled={loading !== null || inactivityLoading}
                  className={`w-full flex items-center justify-between p-4 rounded-xl border ${action.bgColor} ${action.borderColor} hover:brightness-110 disabled:opacity-40 transition-all text-left group relative ${
                    isApplied ? 'ring-2 ring-accent-green/50' : ''
                  }`}
                >
                  <div className="flex items-center gap-3.5">
                    <div className="w-8 h-8 rounded-lg bg-surface-800/80 flex items-center justify-center">
                      {isLoading ? (
                        <Loader2 className={`w-4 h-4 ${action.color} animate-spin`} />
                      ) : isApplied ? (
                        <CheckCircle2 className="w-4 h-4 text-accent-green animate-bounce" />
                      ) : (
                        <Icon className={`w-4 h-4 ${action.color}`} />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${action.color}`}>{action.label}</span>
                        {isApplied && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-accent-green/20 text-accent-green">
                            ✓ Applied to {selectedSymbol}!
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-text-muted mt-0.5">{action.desc}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-themeborder-subtle bg-surface-850">
          <span className="text-[11px] text-text-muted">
            Targeting: <span className="font-semibold text-text-primary">{selectedSymbol}</span>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-surface-700 hover:bg-surface-600 text-text-primary transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
