// Utility function for formatting currency
export function money(n: number | null | undefined, decimals = 2): string {
  if (n == null || isNaN(n)) return '—'
  return (
    '$' +
    Number(n).toLocaleString('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    })
  )
}

export function moneyShort(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return '—'
  if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M'
  if (Math.abs(n) >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K'
  return '$' + n.toFixed(0)
}

export default money