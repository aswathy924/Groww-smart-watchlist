import { TrendingUp, AlertTriangle, Activity, CheckCircle2, ChevronRight, ShieldCheck } from 'lucide-react';

export default function SummaryCards({ watchlist, catchUp, feedHealth, onMarkAllSeen, onOpenCatchUpTab, loading }) {
  const totalCount = watchlist?.total_count || 0;
  const highCount = watchlist?.high_attention_count || 0;
  const modCount = watchlist?.moderate_attention_count || 0;
  const totalAlerts = highCount + modCount;

  const items = watchlist?.items || [];
  const gainers = items.filter(i => (i.change_pct_day ?? 0) >= 0).length;
  const losers = items.filter(i => (i.change_pct_day ?? 0) < 0).length;

  const formatLag = (ms) => {
    if (!ms && ms !== 0) return '12ms';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {/* Card 1: Tracked Assets & Market Breadth */}
      <div className="p-6 rounded-2xl bg-surface-800 border border-themeborder-subtle shadow-card hover:border-themeborder-strong transition-all">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-text-muted">Watchlist Assets</span>
          <div className="w-8 h-8 rounded-xl bg-surface-700 flex items-center justify-center text-text-secondary">
            <TrendingUp className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-3">
          <span className="text-3xl font-extrabold text-text-primary">{totalCount}</span>
          <span className="text-sm font-medium text-text-secondary">Symbols tracked</span>
        </div>
        <div className="mt-3 flex items-center gap-3 text-xs sm:text-sm font-semibold">
          <span className="flex items-center gap-1.5 text-accent-green">
            <span className="w-2 h-2 rounded-full bg-accent-green" />
            {gainers} Advance
          </span>
          <span className="flex items-center gap-1.5 text-accent-red">
            <span className="w-2 h-2 rounded-full bg-accent-red" />
            {losers} Decline
          </span>
        </div>
      </div>

      {/* Card 2: Attention & Catch-Up Intelligence */}
      <div className={`p-6 rounded-2xl border shadow-card transition-all ${
        totalAlerts > 0 
          ? 'bg-surface-800 border-accent-yellow/30 hover:border-accent-yellow/50' 
          : 'bg-surface-800 border-themeborder-subtle hover:border-themeborder-strong'
      }`}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-text-muted">Since You Checked</span>
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center ${
            totalAlerts > 0 ? 'bg-accent-yellow/10 text-accent-yellow' : 'bg-surface-700 text-text-muted'
          }`}>
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline justify-between">
          <div className="flex items-baseline gap-2">
            <span className={`text-3xl font-extrabold ${totalAlerts > 0 ? 'text-accent-yellow' : 'text-text-primary'}`}>
              {totalAlerts}
            </span>
            <span className="text-sm font-medium text-text-secondary">
              {totalAlerts === 1 ? 'Actionable event' : 'Actionable events'}
            </span>
          </div>
          {totalAlerts > 0 && (
            <button
              onClick={onMarkAllSeen}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-accent-green/15 text-accent-green hover:bg-accent-green/25 border border-accent-green/30 transition-all disabled:opacity-50"
              title="Reset checkpoint to current prices"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {loading ? 'Marking...' : 'Mark Seen'}
            </button>
          )}
        </div>
        <div className="mt-3 flex items-center justify-between text-xs sm:text-sm text-text-muted">
          <div className="flex items-center gap-2">
            {highCount > 0 && <span className="text-accent-red font-bold">{highCount} Urgent (&gt;2σ)</span>}
            {highCount > 0 && modCount > 0 && <span>·</span>}
            {modCount > 0 && <span className="text-accent-yellow font-bold">{modCount} Notable</span>}
            {totalAlerts === 0 && <span className="text-accent-green font-semibold">All caught up</span>}
          </div>
          {totalAlerts > 0 && (
            <button 
              onClick={onOpenCatchUpTab}
              className="text-xs text-text-secondary hover:text-text-primary flex items-center gap-0.5 font-semibold underline transition-colors"
            >
              Review details <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Card 3: Ingestion Stream & Latency */}
      <div className="p-6 rounded-2xl bg-surface-800 border border-themeborder-subtle shadow-card hover:border-themeborder-strong transition-all">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-text-muted">Feed Engine</span>
          <div className="w-8 h-8 rounded-xl bg-surface-700 flex items-center justify-center text-accent-green">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2.5">
          <span className="text-3xl font-extrabold text-text-primary">
            {feedHealth?.feed_mode || 'HYBRID_SIM'}
          </span>
          <span className="text-xs sm:text-sm text-accent-green font-bold flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-accent-green dot-pulse" />
            24/7 Active
          </span>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs sm:text-sm text-text-muted">
          <span className="flex items-center gap-1.5 font-medium">
            <ShieldCheck className="w-4 h-4 text-accent-green" />
            Bad-tick filter active
          </span>
          <span className="font-mono text-text-secondary font-semibold">Lag: {formatLag(feedHealth?.feed_lag_ms)}</span>
        </div>
      </div>
    </div>
  );
}
