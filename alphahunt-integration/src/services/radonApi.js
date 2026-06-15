const API_BASE = process.env.REACT_APP_RADON_API_URL || 'http://localhost:8321';

async function request(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      const text = await res.text();
      return { error: `${res.status}: ${text}` };
    }
    return await res.json();
  } catch (err) {
    return { error: err.message || 'Network error' };
  }
}

export const radonApi = {
  async health() {
    return request('/health');
  },

  async getTicker(symbol) {
    return request(`/ticker/${encodeURIComponent(symbol)}`);
  },

  async getFlow(symbol) {
    return request(`/flow/${encodeURIComponent(symbol)}`);
  },

  async getOptions(symbol, expiry) {
    const params = expiry ? `?expiry=${encodeURIComponent(expiry)}` : '';
    return request(`/options/${encodeURIComponent(symbol)}${params}`);
  },

  async getAnalyst(symbol) {
    return request(`/analyst/${encodeURIComponent(symbol)}`);
  },

  async getHistory(symbol, period, interval) {
    const params = new URLSearchParams();
    if (period) params.set('period', period);
    if (interval) params.set('interval', interval);
    const qs = params.toString();
    return request(`/history/${encodeURIComponent(symbol)}${qs ? `?${qs}` : ''}`);
  },

  async getWatchlist() {
    return request('/watchlist');
  },

  async addToWatchlist(symbol) {
    return request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'POST' });
  },

  async removeFromWatchlist(symbol) {
    return request(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' });
  },

  async runScan(tickers, top) {
    const body = {};
    if (tickers) body.tickers = tickers;
    if (top) body.top = top;
    return request('/scan', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  async calculateKelly(params) {
    return request('/kelly', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async getBrokerStatus() {
    return request('/broker/status');
  },

  async getBrokerPositions() {
    return request('/broker/positions');
  },
};
