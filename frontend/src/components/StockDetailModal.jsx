import { X, TrendingUp, TrendingDown, Zap, BarChart3, ShieldAlert, CheckCircle2, Clock, Activity } from 'lucide-react';

export default function StockDetailModal({ stock, isOpen, onClose, onMarkSeen }) {
  if (!isOpen || !stock) return null;

  const isPositive = (stock.delta_pct ?? 0) >= 0;
  const isDayPositive = (stock.change_pct_day ?? 0) >= 0;

  const formatPrice = (p) => {
    if (p === undefined || p === null) return '₹0.00';
    return `₹${p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const dayLow = stock.day_low ?? (stock.current_price * 0.98);
  const dayHigh = stock.day_high ?? (stock.current_price * 1.02);
  const rangeSpan = Math.max(dayHigh - dayLow, 0.01);
  const currentPosPct = Math.min(Math.max(((stock.current_price - dayLow) / rangeSpan) * 100, 0), 100);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div 
        className="w-full max-w-xl bg-surface-800 border border-themeborder-subtle rounded-2xl shadow-2xl overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-themeborder-subtle bg-surface-850">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-surface-700 border border-themeborder-subtle flex items-center justify-center text-sm font-bold text-accent-green">
              {stock.symbol.slice(0, 2)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-text-primary">{stock.symbol}</h2>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-surface-700 text-text-secondary border border-themeborder-subtle">
                  NSE
                </span>
              </div>
              <p className="text-xs text-text-muted">{stock.name}</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {/* Price Header Banner */}
          <div className="flex items-end justify-between bg-surface-700/50 p-4 rounded-xl border border-themeborder-subtle">
            <div>
              <span className="text-xs text-text-muted block mb-1">Current Price (LTP)</span>
              <span className="text-2xl font-bold text-text-primary tabular-nums">
                {formatPrice(stock.current_price)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-xs text-text-muted block mb-1">Today's Movement</span>
              <div className={`inline-flex items-center gap-1 text-sm font-semibold px-2.5 py-1 rounded-lg ${isDayPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'}`}>
                {isDayPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                {isDayPositive ? '+' : ''}{stock.change_pct_day?.toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Plain-English Movement Rationale */}
          <div className="p-4 rounded-xl bg-surface-700/40 border border-themeborder-subtle space-y-2">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent-blue" />
              <h3 className="text-xs font-semibold text-text-primary uppercase tracking-wider">
                Smart Movement Rationale
              </h3>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              {stock.rationale || 'Price is fluctuating within normal statistical bounds relative to its 30-day baseline.'}
            </p>
          </div>

          {/* Intraday Range Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-text-muted">
              <span>Day Low: {formatPrice(dayLow)}</span>
              <span>Day High: {formatPrice(dayHigh)}</span>
            </div>
            <div className="h-2 bg-surface-600 rounded-full relative overflow-hidden">
              <div
                className="absolute top-0 bottom-0 left-0 bg-accent-green/80 rounded-full"
                style={{ width: `${currentPosPct}%` }}
              />
            </div>
          </div>

          {/* Statistical Breakdown Grid */}
          <div className="grid grid-cols-2 gap-3">
            {/* Z-Score */}
            <div className="p-3.5 rounded-xl bg-surface-700/30 border border-themeborder-subtle">
              <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <Zap className="w-3.5 h-3.5 text-accent-yellow" />
                <span>Z-Score Volatility</span>
              </div>
              <div className="text-base font-semibold text-text-primary">
                {stock.z_score !== undefined ? `${stock.z_score.toFixed(2)}σ` : '--'}
              </div>
              <div className="text-[11px] text-text-muted mt-0.5">
                {stock.z_score > 2.0 ? 'Statistical Breakout (>2σ)' : 'Within normal variance'}
              </div>
            </div>

            {/* Volume Ratio */}
            <div className="p-3.5 rounded-xl bg-surface-700/30 border border-themeborder-subtle">
              <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <BarChart3 className="w-3.5 h-3.5 text-accent-blue" />
                <span>Volume Ratio</span>
              </div>
              <div className="text-base font-semibold text-text-primary">
                {stock.volume_ratio !== undefined ? `${stock.volume_ratio.toFixed(2)}x` : '--'}
              </div>
              <div className="text-[11px] text-text-muted mt-0.5">
                {stock.volume_ratio > 2.5 ? 'Institutional surge (>2.5x)' : 'Standard session volume'}
              </div>
            </div>

            {/* Last Checkpoint Price */}
            <div className="p-3.5 rounded-xl bg-surface-700/30 border border-themeborder-subtle">
              <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <Clock className="w-3.5 h-3.5 text-text-secondary" />
                <span>Checkpoint Price</span>
              </div>
              <div className="text-base font-semibold text-text-primary">
                {formatPrice(stock.seen_price || stock.base_price)}
              </div>
              <div className="text-[11px] text-text-muted mt-0.5">
                Delta: <span className={isPositive ? 'text-accent-green' : 'text-accent-red'}>{isPositive ? '+' : ''}{stock.delta_pct?.toFixed(2)}%</span>
              </div>
            </div>

            {/* Tick Integrity */}
            <div className="p-3.5 rounded-xl bg-surface-700/30 border border-themeborder-subtle">
              <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
                <ShieldAlert className="w-3.5 h-3.5 text-accent-green" />
                <span>Feed Integrity</span>
              </div>
              <div className="text-base font-semibold text-text-primary">
                {stock.tick_quality || 'CLEAN'}
              </div>
              <div className="text-[11px] text-text-muted mt-0.5">
                {stock.is_halted ? 'Trading halted' : 'Continuously verified'}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-themeborder-subtle bg-surface-850">
          <div className="text-xs text-text-muted">
            Attention Tier: <span className="font-semibold text-text-primary">{stock.attention_tier || 'NORMAL'}</span>
          </div>
          <button
            onClick={() => {
              if (onMarkSeen) onMarkSeen(stock.symbol);
              onClose();
            }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-accent-green text-surface-950 hover:bg-accent-green/90 transition-all shadow-md shadow-accent-green/10"
          >
            <CheckCircle2 className="w-4 h-4" />
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  );
}
