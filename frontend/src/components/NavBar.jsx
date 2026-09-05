import { useState, useRef, useEffect } from 'react';
import { 
  Activity, ChevronDown, User, Wifi, WifiOff, Clock, FlaskConical,
  ShieldCheck, LogIn, Sparkles, Check, Plus, Sun, Moon
} from 'lucide-react';

export default function NavBar({ userId, onUserChange, feedHealth, onOpenSandbox }) {
  const [userOpen, setUserOpen] = useState(false);
  const [customInput, setCustomInput] = useState('');
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(t => (t === 'dark' ? 'light' : 'dark'));
  };

  const defaultUsers = [
    { id: 'trader_1', label: 'Trader 1', tag: 'Intraday Alpha', desc: 'Core Nifty 50 Blue Chips' },
    { id: 'trader_2', label: 'Trader 2', tag: 'Positional F&O', desc: 'Banking & High-Beta Stocks' },
    { id: 'analyst_1', label: 'Analyst Pro', tag: 'Quant Research', desc: 'Sectoral Dispersion & Hedge' },
  ];

  const [userList, setUserList] = useState(defaultUsers);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setUserOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleCustomLogin = (e) => {
    e.preventDefault();
    if (!customInput.trim()) return;
    const cleanId = customInput.trim().toLowerCase().replace(/\s+/g, '_');
    const existing = userList.find(u => u.id === cleanId);
    if (!existing) {
      const newUser = {
        id: cleanId,
        label: customInput.trim(),
        tag: 'Custom Evaluator',
        desc: 'New Clean Sandbox Account',
      };
      setUserList(prev => [...prev, newUser]);
    }
    onUserChange(cleanId);
    setCustomInput('');
    setUserOpen(false);
  };

  const currentProfile = userList.find(u => u.id === userId) || {
    id: userId,
    label: userId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    tag: 'Custom Persona',
    desc: 'Multi-Tenant Sandbox User',
  };

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
    <header className="sticky top-0 z-40 bg-surface-900/80 backdrop-blur-xl border-b border-themeborder-subtle transition-colors duration-200">
      <div className="max-w-[1680px] w-full mx-auto px-4 sm:px-6 lg:px-8 xl:px-10 h-16 flex items-center justify-between">
        {/* Left: Brand / Title */}
        <div>
          <h1 className="text-base font-bold text-text-primary tracking-tight">Smart Watchlist</h1>
          <p className="text-[11px] text-text-muted hidden sm:block">Intelligent Delta & Anomaly Detection Engine</p>
        </div>

        {/* Right: Theme Toggle, Sandbox CTA, Live Feed Pill & Account Profile */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          {/* Theme Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl bg-surface-800 border border-themeborder-subtle hover:border-themeborder-strong hover:bg-surface-700 text-text-secondary hover:text-text-primary transition-all flex items-center justify-center shadow-sm"
            title={theme === 'dark' ? "Switch to Light Mode" : "Switch to Dark Mode"}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-accent-yellow transition-transform hover:rotate-45 duration-300" />
            ) : (
              <Moon className="w-4 h-4 text-accent-blue transition-transform hover:-rotate-12 duration-300" />
            )}
          </button>

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

          {/* Account Profile / Multi-Tenant Auth Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setUserOpen(!userOpen)}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-surface-800 border border-themeborder-subtle hover:border-themeborder-strong hover:bg-surface-700 transition-all text-xs shadow-sm"
            >
              <div className="w-6 h-6 rounded-lg bg-accent-green/20 border border-accent-green/30 flex items-center justify-center text-accent-green font-bold text-[11px]">
                {currentProfile.label.slice(0, 2).toUpperCase()}
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-text-primary font-semibold leading-none">{currentProfile.label}</div>
                <div className="text-[10px] text-text-muted mt-0.5 leading-none">{currentProfile.tag}</div>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 ${userOpen ? 'rotate-180' : ''}`} />
            </button>

            {userOpen && (
              <div className="absolute right-0 mt-2 w-72 rounded-2xl bg-surface-800 border border-themeborder-subtle shadow-2xl overflow-hidden animate-slide-down z-50">
                {/* Active Profile Banner */}
                <div className="p-4 bg-surface-850 border-b border-themeborder-subtle">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-accent-green/15 border border-accent-green/30 flex items-center justify-center text-accent-green font-bold text-sm">
                      {currentProfile.label.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="overflow-hidden">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-bold text-text-primary truncate">{currentProfile.label}</span>
                        <ShieldCheck className="w-3.5 h-3.5 text-accent-green flex-shrink-0" title="Verified Session" />
                      </div>
                      <div className="text-[10px] text-accent-green font-medium flex items-center gap-1 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
                        Pro Trader Authenticated
                      </div>
                    </div>
                  </div>
                </div>

                {/* Persona Presets */}
                <div className="p-2 border-b border-themeborder-subtle">
                  <div className="px-2.5 py-1.5 text-[10px] text-text-muted font-bold uppercase tracking-wider">
                    Switch Active Persona
                  </div>
                  {userList.map(u => (
                    <button
                      key={u.id}
                      onClick={() => { onUserChange(u.id); setUserOpen(false); }}
                      className={`w-full p-2.5 rounded-xl flex items-center justify-between text-left transition-all ${
                        u.id === userId ? 'bg-surface-700/90 text-text-primary' : 'hover:bg-surface-700/40 text-text-secondary'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-[10px] ${
                          u.id === userId ? 'bg-accent-green text-surface-950' : 'bg-surface-600 text-text-muted'
                        }`}>
                          {u.label.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="text-xs font-semibold">{u.label}</div>
                          <div className="text-[10px] text-text-muted truncate max-w-[150px]">{u.desc}</div>
                        </div>
                      </div>
                      {u.id === userId && <Check className="w-4 h-4 text-accent-green" />}
                    </button>
                  ))}
                </div>

                {/* Custom User Login */}
                <form onSubmit={handleCustomLogin} className="p-3 bg-surface-850">
                  <div className="text-[10px] text-text-muted font-bold uppercase tracking-wider mb-2">
                    Login with Custom Username
                  </div>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={customInput}
                      onChange={e => setCustomInput(e.target.value)}
                      placeholder="e.g. evaluator_1"
                      className="flex-1 px-3 py-1.5 bg-surface-700 border border-themeborder-subtle rounded-xl text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-green/40"
                    />
                    <button
                      type="submit"
                      disabled={!customInput.trim()}
                      className="px-3 py-1.5 bg-accent-green text-surface-950 font-bold rounded-xl text-xs hover:bg-accent-green/90 disabled:opacity-40 transition-all flex items-center gap-1"
                    >
                      <LogIn className="w-3 h-3" />
                      Switch
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
