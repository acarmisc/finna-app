// Re-export from lib/formatting.ts
import { money as moneyFn, moneyShort } from '@/lib/formatting'

export const money = moneyFn
export { moneyShort }

export default moneyFn