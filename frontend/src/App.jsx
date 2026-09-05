import { useState, useEffect, useCallback, useRef } from 'react';
import NavBar from './components/NavBar';
import SummaryCards from './components/SummaryCards';
import CatchUpPanel from './components/CatchUpPanel';
import WatchlistTable from './components/WatchlistTable';
import StockDetailModal from './components/StockDetailModal';
import AddSymbolModal from './components/AddSymbolModal';
import DemoControls from './components/DemoControls';

import {
  getWatchlist,
  getCatchUp,
  postCheckpoint,
  addWatchlistItem,
  removeWatchlistItem,
  getAvailableSymbols,
  getFeedHealth,
} from './api/client';

const POLL_INTERVAL = 3000; // 3s calm live polling

export default function App() {
  // ── State ────────────────────────────────────────────
  const [userId, setUserId] = useState('trader_1');
  const [watchlist, setWatchlist] = useState(null);
  const [catchUp, setCatchUp] = useState(null);
  const [feedHealth, setFeedHealth] = useState(null);
  const [availableSymbols, setAvailableSymbols] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [sandboxOpen, setSandboxOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const pollRef = useRef(null);

  // ── Data fetching ─────────────────────────────────────
  const fetchAll = useCallback(async (uid) => {
    try {
      const [wl, cu, fh] = await Promise.all([
        getWatchlist(uid),
        getCatchUp(uid),
        getFeedHealth(),
      ]);
      setWatchlist(wl);
      setCatchUp(cu);
      setFeedHealth(fh);
      setError(null);
    } catch (err) {
      console.error('Fetch error:', err);
      setError('Backend connection error. Please ensure the backend server is running on port 8000.');
    }
  }, []);

  useEffect(() => {
    fetchAll(userId);
    pollRef.current = setInterval(() => fetchAll(userId), POLL_INTERVAL);
    return () => clearInterval(pollRef.current);
  }, [userId, fetchAll]);

  // Keep selectedStock up to date with fresh price telemetry
  useEffect(() => {
    if (selectedStock && watchlist?.items) {
      const fresh = watchlist.items.find(i => i.symbol === selectedStock.symbol);
      if (fresh) setSelectedStock(fresh);
    }
  }, [watchlist, selectedStock]);

  // ── Handlers ──────────────────────────────────────────
  const handleUserChange = (newUserId) => {
    setUserId(newUserId);
    setWatchlist(null);
    setCatchUp(null);
  };

  const handleMarkAllSeen = async () => {
    setLoading(true);
    try {
      await postCheckpoint(userId);
      await fetchAll(userId);
    } catch (err) {
      console.error('Checkpoint error:', err);
    }
    setLoading(false);
  };

  const handleMarkSingleSeen = async (symbol) => {
    try {
      await postCheckpoint(userId, symbol);
      await fetchAll(userId);
    } catch (err) {
      console.error('Single checkpoint error:', err);
    }
  };

  const handleAddSymbol = async (symbol) => {
    try {
      await addWatchlistItem(userId, symbol);
      await fetchAll(userId);
      const syms = await getAvailableSymbols(userId);
      setAvailableSymbols(syms);
    } catch (err) {
      console.error('Add symbol error:', err);
    }
  };

  const handleRemoveSymbol = async (symbol) => {
    try {
      await removeWatchlistItem(userId, symbol);
      await fetchAll(userId);
    } catch (err) {
      console.error('Remove symbol error:', err);
    }
  };

  const handleOpenAddModal = async () => {
    try {
      const syms = await getAvailableSymbols(userId);
      setAvailableSymbols(syms);
    } catch (err) {
      console.error('Fetch symbols error:', err);
    }
    setAddModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-surface-900 text-text-primary selection:bg-accent-green/20 selection:text-accent-green">
      {/* Navigation Bar */}
      <NavBar 
        userId={userId} 
        onUserChange={handleUserChange} 
        feedHealth={feedHealth} 
        onOpenSandbox={() => setSandboxOpen(true)}
      />

      {/* Main Dashboard Body */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Error notification */}
        {error && (
          <div className="bg-accent-red/10 border border-accent-red/25 text-accent-red text-xs px-4 py-3 rounded-2xl animate-fade-in flex items-center justify-between">
            <span>{error}</span>
            <button 
              onClick={() => fetchAll(userId)} 
              className="underline hover:text-white"
            >
              Retry
            </button>
          </div>
        )}

        {/* 1. Spacious Overview Cards */}
        <SummaryCards
          watchlist={watchlist}
          catchUp={catchUp}
          feedHealth={feedHealth}
          onMarkAllSeen={handleMarkAllSeen}
          loading={loading}
        />

        {/* 2. Catch-Up Intelligence (Only rendered when actionable items exist) */}
        <CatchUpPanel
          catchUpData={catchUp}
          onMarkAllSeen={handleMarkAllSeen}
          onSelectStock={(stock) => setSelectedStock(stock)}
          loading={loading}
        />

        {/* 3. Watchlist Core Table */}
        <WatchlistTable
          watchlistData={watchlist}
          onRemoveSymbol={handleRemoveSymbol}
          onOpenAddModal={handleOpenAddModal}
          onSelectStock={(stock) => setSelectedStock(stock)}
        />
      </main>

      {/* Stock Detail & Telemetry Modal */}
      <StockDetailModal
        stock={selectedStock}
        isOpen={!!selectedStock}
        onClose={() => setSelectedStock(null)}
        onMarkSeen={handleMarkSingleSeen}
      />

      {/* Add Stock Modal */}
      <AddSymbolModal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        availableSymbols={availableSymbols}
        onAdd={handleAddSymbol}
        loading={loading}
      />

      {/* Evaluator Sandbox Modal */}
      <DemoControls 
        isOpen={sandboxOpen} 
        onClose={() => setSandboxOpen(false)} 
        currentUserId={userId}
      />
    </div>
  );
}
