import { useState } from 'react';
import { 
  AlertTriangle, CheckCircle2, TrendingUp, TrendingDown, 
  Zap, BarChart3, ChevronDown, ChevronUp, Sparkles, Check
} from 'lucide-react';

export default function CatchUpPanel({ 
  catchUpData, 
  onMarkAllSeen, 
  onSelectStock, 
  loading 
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!catchUpData || catchUpData.total_flagged === 0) return null;

  const { high_attention = [], moderate_attention = [] } = catchUpData;
  const totalHigh = high_attention.length;
  const totalMod = moderate_attention.length;

  const formatPrice = (p) => {
    if (!p) return '₹0.00';
    return `₹${p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const renderCard = (item) => {
    const isPositive = (item.delta_pct ?? 0) >= 0;

    return (
      <div
        key={item.symbol}
        onClick={() => onSelectStock && onSelectStock(item)}
        className="group p-5 rounded-2xl bg-surface-800 border border-themeborder-subtle hover:border-accent-green/40 hover:bg-surface-700/50 transition-all cursor-pointer shadow-card flex flex-col justify-between"
      >
        <div>
          {/* Card Top: Symbol + Price Delta */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs ${
                item.attention_tier === 'HIGH'
                  ? 'bg-accent-red/10 text-accent-red border border-accent-red/20'
                  : 'bg-accent-yellow/10 text-accent-yellow border border-accent-yellow/20'
              }`}>
                {item.symbol.slice(0, 2)}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-text-primary text-sm">{item.symbol}</h4>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    item.attention_tier === 'HIGH' ? 'badge-high' : 'badge-moderate'
                  }`}>
                    {item.attention_tier === 'HIGH' ? 'Urgent Breakout' : 'Notable'}
                  </span>
                </div>
                <p className="text-xs text-text-muted truncate max-w-[140px]">{item.name}</p>
              </div>
            </div>

            {/* Price change pill */}
            <div className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold tabular-nums ${
              isPositive ? 'bg-accent-green/10 text-accent-green' : 'bg-accent-red/10 text-accent-red'
            }`}>
              {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
              {isPositive ? '+' : ''}{item.delta_pct?.toFixed(2)}%
            </div>
          </div>

          {/* Rationale Text */}
          <p className="text-xs text-text-secondary leading-relaxed mb-4 line-clamp-2">
            {item.rationale}
          </p>
        </div>

        {/* Card Bottom: Telemetry Signals */}
        <div className="pt-3 border-t border-themeborder-subtle flex items-center justify-between text-xs text-text-muted">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Zap className="w-3 h-3 text-accent-yellow" />
              <span className="text-text-primary font-medium">{item.z_score?.toFixed(1)}σ</span>
            </span>
            {item.volume_ratio > 1.0 && (
              <span className="flex items-center gap-1">
                <BarChart3 className="w-3 h-3 text-accent-blue" />
                <span className="text-text-primary font-medium">{item.volume_ratio?.toFixed(1)}x</span>
              </span>
            )}
          </div>
          <span className="font-bold text-text-primary tabular-nums">
            {formatPrice(item.current_price)}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-surface-850 border border-themeborder-subtle rounded-2xl p-6 shadow-card space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent-yellow/10 border border-accent-yellow/20 flex items-center justify-center text-accent-yellow">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-text-primary">What Changed Since Your Last Visit</h3>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-accent-yellow/10 text-accent-yellow font-bold border border-accent-yellow/20">
                {catchUpData.total_flagged} Actionable
              </span>
            </div>
            <p className="text-xs sm:text-sm text-text-muted mt-0.5">
              {totalHigh > 0 && <span className="text-accent-red font-bold">{totalHigh} statistical breakouts (&gt;2σ)</span>}
              {totalHigh > 0 && totalMod > 0 && <span> · </span>}
              {totalMod > 0 && <span className="text-accent-yellow font-bold">{totalMod} volume & level breaches</span>}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onMarkAllSeen}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-accent-green/10 text-accent-green border border-accent-green/20 hover:bg-accent-green/20 transition-all disabled:opacity-50"
          >
            <Check className="w-3.5 h-3.5" />
            {loading ? 'Updating...' : 'Mark All As Seen'}
          </button>
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
          >
            {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Grid of Actionable Cards */}
      {!isCollapsed && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
          {high_attention.map(item => renderCard(item))}
          {moderate_attention.map(item => renderCard(item))}
        </div>
      )}
    </div>
  );
}
