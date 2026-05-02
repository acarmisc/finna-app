import { money, moneyShort } from './money'

describe('money', () => {
  it('should format positive numbers with default decimals', () => {
    expect(money(1234.56)).toBe('$1,234.56')
    expect(money(1000)).toBe('$1,000.00')
    expect(money(0)).toBe('$0.00')
  })

  it('should format negative numbers', () => {
    expect(money(-500.5)).toBe('$-500.50')
  })

  it('should handle custom decimal places', () => {
    expect(money(1234.567, 1)).toBe('$1,234.6')
    expect(money(1234.567, 3)).toBe('$1,234.567')
  })

  it('should return em dash for null', () => {
    expect(money(null)).toBe('—')
  })

  it('should return em dash for undefined', () => {
    expect(money(undefined)).toBe('—')
  })

  it('should return em dash for NaN', () => {
    expect(money(NaN)).toBe('—')
  })

  it('should handle zero', () => {
    expect(money(0)).toBe('$0.00')
  })

  it('should handle large numbers', () => {
    expect(money(1000000)).toBe('$1,000,000.00')
    expect(money(123456789)).toBe('$123,456,789.00')
  })
})

describe('moneyShort', () => {
  it('should format numbers in thousands (K)', () => {
    expect(moneyShort(1000)).toBe('$1.0K')
    expect(moneyShort(1500)).toBe('$1.5K')
    expect(moneyShort(999)).toBe('$999')
  })

  it('should format numbers in millions (M)', () => {
    expect(moneyShort(1000000)).toBe('$1.00M')
    expect(moneyShort(2500000)).toBe('$2.50M')
  })

  it('should return em dash for null', () => {
    expect(moneyShort(null)).toBe('—')
  })

  it('should return em dash for undefined', () => {
    expect(moneyShort(undefined)).toBe('—')
  })

  it('should return em dash for NaN', () => {
    expect(moneyShort(NaN)).toBe('—')
  })

  it('should handle zero', () => {
    expect(moneyShort(0)).toBe('$0')
  })

  it('should handle negative numbers', () => {
    expect(moneyShort(-1000)).toBe('$-1.0K')
    expect(moneyShort(-1000000)).toBe('$-1.00M')
  })

  it('should use no decimal places for regular amounts', () => {
    expect(moneyShort(500)).toBe('$500')
  })
})
