import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Watchlist ────────────────────────────────────────────────

export const getWatchlist = (userId = 'trader_1') =>
  api.get(`/api/watchlist`, { params: { user_id: userId } }).then(r => r.data);

export const getCatchUp = (userId = 'trader_1') =>
  api.get(`/api/watchlist/catch-up`, { params: { user_id: userId } }).then(r => r.data);

export const postCheckpoint = (userId = 'trader_1', symbols = null) => {
  const symArray = symbols ? (Array.isArray(symbols) ? symbols : [symbols]) : null;
  return api.post(`/api/watchlist/checkpoint`, { symbols: symArray }, { params: { user_id: userId } }).then(r => r.data);
};

export const addWatchlistItem = (userId = 'trader_1', symbol) =>
  api.post(`/api/watchlist/items`, { symbol }, { params: { user_id: userId } }).then(r => r.data);

export const removeWatchlistItem = (userId = 'trader_1', symbol) =>
  api.delete(`/api/watchlist/items/${symbol}`, { params: { user_id: userId } }).then(r => r.data);

export const getAvailableSymbols = (userId = 'trader_1') =>
  api.get(`/api/watchlist/symbols`, { params: { user_id: userId } }).then(r => r.data);

// ── System ───────────────────────────────────────────────────

export const getFeedHealth = () =>
  api.get(`/api/system/feed-health`).then(r => r.data);

// ── Test / Demo ──────────────────────────────────────────────

export const injectAnomaly = (symbol, anomalyType, durationSeconds = null) =>
  api.post(`/api/test/inject-anomaly`, {
    symbol,
    anomaly_type: anomalyType,
    duration_seconds: durationSeconds,
  }).then(r => r.data);

export default api;
