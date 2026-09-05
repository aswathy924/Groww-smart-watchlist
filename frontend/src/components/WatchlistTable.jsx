import { useState } from 'react';
import { 
  TrendingUp, TrendingDown, AlertTriangle, ShieldAlert, Trash2, 
  Search, ArrowUpDown, Plus, Sparkles, Zap, ChevronRight, BarChart2
} from 'lucide-react';

export default function WatchlistTable({ 
  watchlistData, 
  onRemoveSymbol, 
  onOpenAddModal, 
  onSelectStock 
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTier, setFilterTier] = useState('ALL'); // ALL, ATTENTION, GAINERS, LOSERS
  const [sortKey, setSortKey] = useState('attention_tier');
  const [sortDir, setSortDir] = useState('asc');

  if (!watchlistData || !watchlistData.items || watchlistData.items.length === 0) {
    return (
      <div className="bg-surface-800 border border-white/[0.06] rounded-2xl p-16 text-center shadow-card">
        <div className="w-16 h-16 rounded-2xl bg-surface-700 border border-white/5 flex items-center justify-center mx-auto mb-4 text-text-muted">
          <BarChart2 className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold text-text-primary mb-1">Your watchlist is empty</h3>
        <p className="text-sm text-text-muted max-w-sm mx-auto mb-6">
          Track high-growth Indian blue chips and get real-time statistical breakout alerts.
        </p>
        <button
          onClick={onOpenAddModal}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-accent-green text-surface-950 hover:bg-accent-green/90 transition-all shadow-lg shadow-accent-green/10"
        >
          <Plus className="w-4 h-4" />
          Add First Stock
        </button>
      </div>
    );
  }

  const items = [...watchlistData.items];

  // Filter
  const filtered = items.filter(item => {
    const q = searchQuery.toLowerCase();
    const matchSearch = item.symbol.toLowerCase().includes(q) || item.name.toLowerCase().includes(q);
    if (!matchSearch) return false;

    if (filterTier === 'ATTENTION') {
      return item.attention_tier === 'HIGH' || item.attention_tier === 'MODERATE';
    }
    if (filterTier === 'GAINERS') {
      return (item.change_pct_day ?? 0) > 0;
    }
    if (filterTier === 'LOSERS') {
      return (item.change_pct_day ?? 0) < 0;
    }
    return true;
  });

  // Sort
  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const tierRank = { HIGH: 0, MODERATE: 1, NORMAL: 2 };
  filtered.sort((a, b) => {
    let aVal, bVal;
    switch (sortKey) {
      case 'symbol':         aVal = a.symbol; bVal = b.symbol; break;
      case 'current_price':  aVal = a.current_price; bVal = b.current_price; break;
      case 'delta_pct':      aVal = Math.abs(a.delta_pct ?? 0); bVal = Math.abs(b.delta_pct ?? 0); break;
      case 'change_pct_day': aVal = a.change_pct_day ?? 0; bVal = b.change_pct_day ?? 0; break;
      case 'volume_ratio':   aVal = a.volume_ratio ?? 0; bVal = b.volume_ratio ?? 0; break;
      case 'attention_tier':
      default:
        aVal = tierRank[a.attention_tier] ?? 99;
        bVal = tierRank[b.attention_tier] ?? 99;
        break;
    }
    if (typeof aVal === 'string') {
      return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
  });

  const formatPrice = (p) => {
    if (p === undefined || p === null) return '₹0.00';
    return `₹${p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const AttentionBadge = ({ tier, quality, halted }) => {
    if (halted) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-accent-purple/15 text-accent-purple border border-accent-purple/25">
          <ShieldAlert className="w-3.5 h-3.5" /> Circuit Limit
        </span>
      );
    }
    if (quality === 'SUSPECT_TICK' || quality === 'UNVERIFIED_DATA') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold badge-suspect">
          <AlertTriangle className="w-3 h-3" /> Unverified Data
        </span>
      );
    }
    if (tier === 'HIGH') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold badge-high">
          <Zap className="w-3 h-3" /> Urgent Breakout
        </span>
      );
    }
    if (tier === 'MODERATE') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold badge-moderate">
          <Sparkles className="w-3 h-3" /> Notable Move
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium text-text-muted bg-surface-700/60 border border-white/5">
        Normal Range
      </span>
    );
  };

  const MiniSparkline = ({ dayOpen = 100, dayHigh = 105, dayLow = 95, currentPrice = 102, isPositive = true, symbol = '' }) => {
    const min = Math.min(dayOpen, dayLow, currentPrice);
    const max = Math.max(dayOpen, dayHigh, currentPrice);
    const range = (max - min) || 1.0;
    
    const getY = (val) => Math.round(24 - ((val - min) / range) * 18);
    
    const yOpen = getY(dayOpen);
    const yLow = getY(dayLow);
    const yHigh = getY(dayHigh);
    const yCurr = getY(currentPrice);
    
    const pathD = `M 2 ${yOpen} Q 18 ${yLow}, 36 ${(yLow + yHigh) / 2} T 70 ${yCurr}`;
    const strokeColor = isPositive ? '#00D09C' : '#FF5C5C';
    const gradId = `spark-${symbol}-${isPositive ? 'up' : 'down'}`;

    return (
      <div className="w-20 h-7 flex items-center justify-center">
        <svg className="w-full h-full overflow-visible" viewBox="0 0 74 28">
          <defs>
            <linearGradient id={gradId} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.25" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path d={`${pathD} L 70 28 L 2 28 Z`} fill={`url(#${gradId})`} />
          <path d={pathD} fill="none" stroke={strokeColor} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="70" cy={yCurr} r="2.5" fill={strokeColor} />
        </svg>
      </div>
    );
  };

  return (
    <div className="bg-surface-800 border border-white/[0.06] rounded-2xl shadow-card overflow-hidden">
      {/* Table Toolbar */}
      <div className="p-5 border-b border-white/[0.06] flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: Filter Tabs */}
        <div className="flex items-center gap-1 bg-surface-850 p-1 rounded-xl border border-white/5">
          <button
            onClick={() => setFilterTier('ALL')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterTier === 'ALL'
                ? 'bg-surface-700 text-text-primary shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            All Stocks ({items.length})
          </button>
          <button
            onClick={() => setFilterTier('ATTENTION')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterTier === 'ATTENTION'
                ? 'bg-accent-yellow/15 text-accent-yellow shadow-sm border border-accent-yellow/20'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <Zap className="w-3 h-3" />
            Urgent / Breakout ({items.filter(i => i.attention_tier === 'HIGH' || i.attention_tier === 'MODERATE').length})
          </button>
          <button
            onClick={() => setFilterTier('GAINERS')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterTier === 'GAINERS'
                ? 'bg-accent-green/15 text-accent-green shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Gainers
          </button>
          <button
            onClick={() => setFilterTier('LOSERS')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              filterTier === 'LOSERS'
                ? 'bg-accent-red/15 text-accent-red shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            Losers
          </button>
        </div>

        {/* Right: Search + Add */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search company or symbol..."
              className="w-56 pl-9 pr-3 py-2 bg-surface-700 border border-white/10 rounded-xl text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-green/40 focus:ring-1 focus:ring-accent-green/20 transition-all"
            />
          </div>

          <button
            onClick={onOpenAddModal}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-accent-green text-surface-950 hover:bg-accent-green/90 transition-all shadow-md shadow-accent-green/10 whitespace-nowrap"
          >
            <Plus className="w-4 h-4" />
            Add Stock
          </button>
        </div>
      </div>

      {/* Table Area */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06] text-[11px] font-semibold text-text-muted uppercase tracking-wider bg-surface-850/40">
              <th 
                className="py-3.5 px-6 cursor-pointer hover:text-text-secondary select-none"
                onClick={() => handleSort('symbol')}
              >
                <div className="flex items-center gap-1.5">
                  <span>Instrument</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th 
                className="py-3.5 px-6 cursor-pointer hover:text-text-secondary select-none"
                onClick={() => handleSort('current_price')}
              >
                <div className="flex items-center gap-1.5">
                  <span>LTP & Day Change</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3.5 px-6 select-none">
                <span>Intraday Trend</span>
              </th>
              <th 
                className="py-3.5 px-6 cursor-pointer hover:text-text-secondary select-none"
                onClick={() => handleSort('delta_pct')}
              >
                <div className="flex items-center gap-1.5">
                  <span>Since Last Check</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th 
                className="py-3.5 px-6 cursor-pointer hover:text-text-secondary select-none"
                onClick={() => handleSort('volume_ratio')}
              >
                <div className="flex items-center gap-1.5">
                  <span>Volume Activity</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th 
                className="py-3.5 px-6 cursor-pointer hover:text-text-secondary select-none"
                onClick={() => handleSort('attention_tier')}
              >
                <div className="flex items-center gap-1.5">
                  <span>Attention Tier</span>
                  <ArrowUpDown className="w-3 h-3" />
                </div>
              </th>
              <th className="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-xs text-text-muted">
                  No stocks match your filter or search criteria.
                </td>
              </tr>
            ) : (
              filtered.map((item) => {
                const isDayPositive = (item.change_pct_day ?? 0) >= 0;
                const isDeltaPositive = (item.delta_pct ?? 0) >= 0;

                return (
                  <tr
                    key={item.symbol}
                    onClick={() => onSelectStock && onSelectStock(item)}
                    className="hover:bg-surface-700/40 cursor-pointer transition-colors duration-150 group"
                  >
                    {/* Instrument */}
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-surface-700 border border-white/5 flex items-center justify-center text-xs font-bold text-text-primary group-hover:border-accent-green/30 group-hover:text-accent-green transition-all">
                          {item.symbol.slice(0, 2)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-text-primary text-sm">{item.symbol}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-700 text-text-muted">
                              NSE
                            </span>
                          </div>
                          <p className="text-xs text-text-muted truncate max-w-[150px]">{item.name}</p>
                        </div>
                      </div>
                    </td>

                    {/* LTP & Day Change */}
                    <td className="py-4 px-6">
                      <div className="font-bold text-text-primary text-sm tabular-nums">
                        {formatPrice(item.current_price)}
                      </div>
                      <div className={`inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums mt-0.5 ${isDayPositive ? 'price-up' : 'price-down'}`}>
                        {isDayPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {isDayPositive ? '+' : ''}{item.change_pct_day?.toFixed(2)}%
                      </div>
                    </td>

                    {/* Mini Sparkline Micro-Trend */}
                    <td className="py-4 px-6">
                      <MiniSparkline
                        dayOpen={item.day_open || item.current_price}
                        dayHigh={item.day_high || item.current_price}
                        dayLow={item.day_low || item.current_price}
                        currentPrice={item.current_price}
                        isPositive={isDayPositive}
                        symbol={item.symbol}
                      />
                    </td>

                    {/* Since Last Check */}
                    <td className="py-4 px-6">
                      <div className={`text-xs font-semibold tabular-nums ${isDeltaPositive ? 'text-accent-green' : 'text-accent-red'}`}>
                        {isDeltaPositive ? '+' : ''}{item.delta_pct?.toFixed(2)}%
                      </div>
                      <div className="text-[11px] text-text-muted mt-0.5 flex items-center gap-1.5">
                        <span>Z: {item.z_score !== undefined ? `${item.z_score.toFixed(1)}σ` : '--'}</span>
                        {item.z_score > 2.0 && (
                          <span className="text-accent-yellow font-medium">⚡ Breakout</span>
                        )}
                      </div>
                    </td>
                    {/* Volume Activity */}
                    <td className="py-4 px-6">
                      <div className="text-xs font-semibold text-text-primary tabular-nums">
                        {item.volume_ratio !== undefined ? `${item.volume_ratio.toFixed(2)}x` : '--'}
                      </div>
                      <div className="text-[11px] text-text-muted mt-0.5">
                        {item.volume_ratio >= 2.5 ? (
                          <span className="text-accent-red font-medium">🔥 Heavy Surge</span>
                        ) : item.volume_ratio >= 1.5 ? (
                          <span className="text-accent-yellow font-medium">Above Avg</span>
                        ) : (
                          'Normal Session'
                        )}
                      </div>
                    </td>

                    {/* Attention Tier */}
                    <td className="py-4 px-6">
                      <AttentionBadge 
                        tier={item.attention_tier} 
                        quality={item.tick_quality} 
                        halted={item.is_halted} 
                      />
                    </td>

                    {/* Actions */}
                    <td className="py-4 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => onSelectStock && onSelectStock(item)}
                          className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
                          title="View telemetry insights"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onRemoveSymbol(item.symbol)}
                          className="p-2 rounded-lg text-text-muted hover:text-accent-red hover:bg-accent-red/10 transition-colors"
                          title={`Remove ${item.symbol}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

