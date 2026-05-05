// Re-export from split modules for backward compatibility
// These exports are DEPRECATED - please import directly from:
//   - lib/cn.ts for classnames
//   - lib/formatting.ts for money()
import { cn } from './cn'
import { money, moneyShort } from './formatting'

export { cn, money, moneyShort }

// Also export directly
export { money as formatCurrency, moneyShort as formatCurrencyShort } from './formatting'