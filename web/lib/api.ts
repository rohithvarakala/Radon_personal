const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8321";

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// --- Response types ---

export interface TickerData {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number | null;
  price: number | null;
  previous_close: number | null;
  volume: number | null;
  avg_volume: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  dividend_yield: number | null;
  beta: number | null;
  short_ratio: number | null;
  short_percent_of_float: number | null;
}

export interface TickerResponse {
  ticker: string;
  valid: boolean;
  data?: TickerData;
  error?: string;
}

export interface AnalystResponse {
  ticker: string;
  target_mean_price: number | null;
  target_high_price: number | null;
  target_low_price: number | null;
  recommendation_key: string | null;
  number_of_analyst_opinions: number | null;
  recommendations: Record<string, unknown>[];
}

export interface PutCallRatio {
  ticker: string;
  ratio: number | null;
  signal: "BEARISH" | "LEAN_BEARISH" | "NEUTRAL" | "LEAN_BULLISH" | "BULLISH" | "NO_DATA";
  total_call_volume: number;
  total_put_volume: number;
}

export interface IVData {
  ticker: string;
  current_price: number | null;
  nearest_expiry: string | null;
  atm_call_iv: number | null;
  atm_put_iv: number | null;
  avg_atm_iv: number | null;
}

export interface ShortInterest {
  ticker: string;
  short_ratio: number | null;
  short_percent_of_float: number | null;
  shares_short: number | null;
  shares_short_prior_month: number | null;
  date_short_interest: number | null;
}

export interface FlowResponse {
  ticker: string;
  options_flow: {
    ticker: string;
    source: string;
    put_call_ratio?: PutCallRatio;
    put_call_ratio_error?: string;
    iv_data?: IVData;
    iv_error?: string;
    nearest_expiry?: string;
    num_expirations?: number;
    num_calls?: number;
    num_puts?: number;
    chain_error?: string;
  };
  institutional_signals: {
    ticker: string;
    source: string;
    short_interest?: ShortInterest;
    short_interest_error?: string;
    institutional_holders?: Record<string, unknown>[];
    num_institutional_holders?: number;
    holders_error?: string;
  };
}

export interface WatchlistItem {
  ticker: string;
}

export interface WatchlistMutationResponse {
  status: string;
  ticker: string;
}
