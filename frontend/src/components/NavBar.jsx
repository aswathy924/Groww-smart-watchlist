import { useState, useRef, useEffect } from 'react';
import { Activity, ChevronDown, User, Wifi, WifiOff, Clock, FlaskConical } from 'lucide-react';

export default function NavBar({ userId, onUserChange, feedHealth, onOpenSandbox }) {
  const [userOpen, setUserOpen] = useState(false);
  const dropdownRef = useRef(null);

  const users = [
    { id: 'trader_1', label: 'Trader 1', desc: 'Large-cap Core Watchlist' },
    { id: 'trader_2', label: 'Trader 2', desc: 'Banking & IT Sector' },
  ];

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setUserOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const currentUser = users.find(u => u.id === userId) || users[0];

  const feedStatusConfig = {
    LIVE:    { class: 'feed-live', icon: Wifi, dot: 'bg-accent-green' },
    DELAYED: { class: 'feed-delayed', icon: Clock, dot: 'bg-accent-yellow' },
    STALE:   { class: 'feed-stale', icon: WifiOff, dot: 'bg-accent-red' },
  };

  const feedCfg = feedStatusConfig[feedHealth?.feed_status] || feedStatusConfig.LIVE;
  const FeedIcon = feedCfg.icon;

  const formatLag = (ms) => {
    if (!ms && ms !== 0) return '12ms';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <header className="sticky top-0 z-40 bg-surface-900/80 backdrop-blur-xl border-b border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Left: Brand / Title */}
        <div>
          <h1 className="text-base font-bold text-text-primary tracking-tight">Smart Watchlist</h1>
          <p className="text-[11px] text-text-muted hidden sm:block">Intelligent Delta & Anomaly Detection Engine</p>
        </div>

        {/* Right: Sandbox CTA, Live Feed Pill & User Switcher */}
        <div className="flex items-center gap-3">
          {/* Sandbox Button */}
          <button
            onClick={onOpenSandbox}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-accent-yellow/10 border border-accent-yellow/20 hover:bg-accent-yellow/20 text-accent-yellow transition-all text-xs font-semibold"
            title="Inject deterministic edge cases"
          >
            <FlaskConical className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Simulate Edge Cases</span>
            <span className="sm:hidden">Sandbox</span>
          </button>

          {/* Feed Health Indicator */}
          <div className={`${feedCfg.class} hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold`}>
            <span className={`w-2 h-2 rounded-full ${feedCfg.dot} ${feedHealth?.feed_status === 'LIVE' ? 'dot-pulse' : ''}`} />
            <FeedIcon className="w-3.5 h-3.5" />
            <span>{feedHealth?.feed_status || 'LIVE'}</span>
            <span className="font-mono text-[11px] opacity-75">({formatLag(feedHealth?.feed_lag_ms)})</span>
          </div>

          {/* User Profile Selector */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setUserOpen(!userOpen)}
              className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-xl bg-surface-800 border border-white/10 hover:border-white/20 hover:bg-surface-700 transition-all text-xs"
            >
              <div className="w-6 h-6 rounded-full bg-accent-green/20 flex items-center justify-center text-accent-green font-bold">
                <User className="w-3.5 h-3.5" />
              </div>
              <span className="text-text-primary font-semibold">{currentUser.label}</span>
              <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${userOpen ? 'rotate-180' : ''}`} />
            </button>

            {userOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-surface-800 border border-white/10 shadow-2xl overflow-hidden animate-slide-down">
                <div className="p-3 border-b border-white/[0.06] text-[11px] text-text-muted font-medium uppercase tracking-wider">
                  Select Active Persona
                </div>
                {users.map(user => (
                  <button
                    key={user.id}
                    onClick={() => { onUserChange(user.id); setUserOpen(false); }}
                    className={`w-full p-3.5 flex items-center gap-3 text-left transition-colors ${
                      user.id === userId ? 'bg-surface-700' : 'hover:bg-surface-700/50'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                      user.id === userId ? 'bg-accent-green text-surface-950' : 'bg-surface-600 text-text-muted'
                    }`}>
                      {user.label.slice(-1)}
                    </div>
                    <div>
                      <div className={`text-xs font-semibold ${user.id === userId ? 'text-accent-green' : 'text-text-primary'}`}>
                        {user.label}
                      </div>
                      <div className="text-[11px] text-text-muted">{user.desc}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
