export const fmt = {
  money: (n: number, opts: { compact?: boolean } = {}) => {
    const abs = Math.abs(n);
    if (opts.compact && abs >= 1_000_000) return '$' + (n / 1_000_000).toFixed(2) + 'M';
    if (opts.compact && abs >= 10_000) return '$' + (n / 1_000).toFixed(1) + 'K';
    return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },
  pct: (n: number) => (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(1) + '%',
  int: (n: number) => n.toLocaleString('en-US'),
};
