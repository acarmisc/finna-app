import { useEffect } from 'react';
import type { Theme, Density, Accent } from '../types';
import { useLocalStorage } from './useLocalStorage';

const ACCENT_COLORS: Record<Accent, { brand: string; weak: string; ink: string }> = {
  green: { brand: 'oklch(0.58 0.14 150)', weak: 'oklch(0.95 0.045 150)', ink: 'oklch(0.38 0.10 150)' },
  indigo: { brand: 'oklch(0.52 0.18 275)', weak: 'oklch(0.96 0.04 275)', ink: 'oklch(0.34 0.14 275)' },
  amber: { brand: 'oklch(0.70 0.17 75)', weak: 'oklch(0.96 0.05 85)', ink: 'oklch(0.44 0.12 75)' },
  slate: { brand: 'oklch(0.40 0.020 265)', weak: 'oklch(0.95 0.005 265)', ink: 'oklch(0.22 0.012 265)' },
};

export function useTheme() {
  const [theme, setTheme] = useLocalStorage<Theme>('finna-theme', 'light');
  const [density, setDensity] = useLocalStorage<Density>('finna-density', 'compact');
  const [accent, setAccent] = useLocalStorage<Accent>('finna-accent', 'slate');

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    document.body.className = density === 'compact' ? 'density-compact' : '';

    const accentColors = ACCENT_COLORS[accent];
    root.style.setProperty(`--accent-${accent}-brand`, accentColors.brand);
    root.style.setProperty(`--accent-${accent}-weak`, accentColors.weak);
    root.style.setProperty(`--accent-${accent}-ink`, accentColors.ink);
    root.style.setProperty('--primary', accentColors.brand);
    root.style.setProperty('--ring', accentColors.brand);
  }, [theme, density, accent]);

  return {
    theme,
    density,
    accent,
    setTheme,
    setDensity,
    setAccent,
  };
}
