import { useQuery, useMutation } from '@tanstack/react-query';

const API_BASE = `${import.meta.env.VITE_API_BASE_URL}/cashflow`;

export const useOpeningClosingBalance = () => {
    return useQuery({
        queryKey: ['cashflow', 'ocbal'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/ocbal`);
            if (!res.ok) throw new Error('Failed to fetch opening/closing balance');
            return res.json();
        },
    });
};

export type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
};

export type QueryPayload = {
    query: string;
    history: ChatMessage[];
};

export const useCashflowAgentQuery = () => {
    return useMutation({
        mutationFn: async (payload: QueryPayload) => {
            // Build context from history
            let fullQuery = payload.query;
            if (payload.history.length > 0) {
                const context = payload.history
                    .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
                    .join('\n');
                fullQuery = `Previous conversation:\n${context}\n\nCurrent question: ${payload.query}`;
            }
            
            // Use GET with query parameter (matching backend)
            const res = await fetch(`${API_BASE}/query?query=${encodeURIComponent(fullQuery)}`);
            if (!res.ok) throw new Error('Failed to query agent');
            return res.json();
        },
    });
};

export type MarketIndicator = {
    value: number;
    zscore?: number;
    yield?: number;
    day_change?: number;
    explanation: string;
};

export type MarketRegimeResponse = {
    score: number;
    regime: 'High' | 'Medium' | 'Low';
    regime_explanation: string;
    indicators: {
        vix: MarketIndicator;
        net_flow: MarketIndicator;
        ad_ratio: MarketIndicator;
        bond_10y: MarketIndicator;
    };
};

export const useMarketRegime = () => {
    return useQuery<MarketRegimeResponse>({
        queryKey: ['cashflow', 'marketregime'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/marketregime`);
            if (!res.ok) throw new Error('Failed to fetch market regime');
            return res.json();
        },
    });
};


export const useLiquidityRegime = () => {
    return useQuery({
        queryKey: ['cashflow', 'liqregime'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/liqregime`);
            if (!res.ok) throw new Error('Failed to fetch liquidity regime');
            return res.json();
        },
    });
};

export const useInAndOutFlow = () => {
    return useQuery({
        queryKey: ['cashflow', 'inandoutflow'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/inandoutflow`);
            if (!res.ok) throw new Error('Failed to fetch in/out flow');
            return res.json();
        },
    });
};

export const useCashBalanceForecast = () => {
    return useQuery({
        queryKey: ['cashflow', 'cashbalanceforecast'],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/cashbalanceforecast`);
            if (!res.ok) throw new Error('Failed to fetch cash balance forecast');
            return res.json();
        },
    });
};