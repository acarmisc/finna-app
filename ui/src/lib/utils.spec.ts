import { cn } from './utils'

describe('cn utility function', () => {
  it('should merge class names correctly', () => {
    expect(cn('bg-red-500', 'text-white')).toBe('bg-red-500 text-white')
  })

  it('should handle falsy values', () => {
    expect(cn('bg-red-500', false, 'text-white', null, undefined, 0)).toBe('bg-red-500 text-white')
  })

  it('should handle nested arrays', () => {
    expect(cn(['bg-red-500', 'p-4'], 'text-white')).toContain('bg-red-500')
    expect(cn(['bg-red-500', 'p-4'], 'text-white')).toContain('p-4')
    expect(cn(['bg-red-500', 'p-4'], 'text-white')).toContain('text-white')
  })

  it('should handle ClassValue objects', () => {
    // This test assumes clsx handles objects correctly
    const result = cn({'bg-red-500': true, 'p-4': false}, 'text-white')
    expect(result).toContain('bg-red-500')
    expect(result).not.toContain('p-4')
    expect(result).toContain('text-white')
  })
})