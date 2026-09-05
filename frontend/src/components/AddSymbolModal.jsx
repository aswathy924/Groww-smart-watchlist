import { useState } from 'react';
import { Search, Plus, X, Check, AlertCircle, Sparkles } from 'lucide-react';

export default function AddSymbolModal({ isOpen, onClose, availableSymbols, onAdd, loading }) {
  const [searchQuery, setSearchQuery] = useState('');

  if (!isOpen) return null;

  const filtered = (availableSymbols || []).filter(s => {
    const q = searchQuery.toLowerCase();
    return s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q) || s.sector.toLowerCase().includes(q);
  });

  const formatPrice = (p) => {
    if (!p) return '₹0.00';
    return `₹${p.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div 
        className="w-full max-w-lg bg-surface-800 border border-themeborder-subtle rounded-2xl shadow-2xl overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-themeborder-subtle bg-surface-850">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-accent-green/10 flex items-center justify-center text-accent-green">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-text-primary">Add Instruments</h2>
              <p className="text-xs text-text-muted">Search from 15 high-liquidity NSE blue-chip stocks</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search */}
        <div className="p-6 pb-2">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by ticker (e.g. RELIANCE), company, or sector..."
              className="w-full pl-10 pr-4 py-3 bg-surface-700 border border-themeborder-subtle rounded-xl text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-green/40 focus:ring-1 focus:ring-accent-green/20 transition-all"
              autoFocus
            />
          </div>
        </div>

        {/* Symbol list */}
        <div className="max-h-80 overflow-y-auto px-4 pb-6 space-y-2">
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-text-muted">
              <AlertCircle className="w-6 h-6" />
              <span className="text-xs">No matching symbols found</span>
            </div>
          ) : (
            filtered.map(sym => (
              <div
                key={sym.symbol}
                className={`flex items-center justify-between p-3.5 rounded-xl border border-themeborder-subtle transition-all ${
                  sym.is_tracked 
                    ? 'bg-surface-850/40 opacity-60' 
                    : 'bg-surface-700/40 hover:bg-surface-700 hover:border-themeborder-strong'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-surface-600 flex items-center justify-center text-xs font-bold text-text-primary">
                    {sym.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text-primary text-sm">{sym.symbol}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-600 text-text-muted">
                        {sym.sector}
                      </span>
                    </div>
                    <div className="text-xs text-text-muted">{sym.name}</div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-xs font-semibold text-text-primary tabular-nums">
                    {formatPrice(sym.base_price)}
                  </span>
                  {sym.is_tracked ? (
                    <span className="flex items-center gap-1 text-xs font-medium text-accent-green bg-accent-green/10 px-2.5 py-1 rounded-lg">
                      <Check className="w-3.5 h-3.5" /> Added
                    </span>
                  ) : (
                    <button
                      onClick={() => onAdd(sym.symbol)}
                      disabled={loading}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold bg-accent-green text-surface-950 hover:bg-accent-green/90 transition-all shadow-sm disabled:opacity-50"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
