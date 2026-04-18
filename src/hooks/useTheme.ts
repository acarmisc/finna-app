import { useState, useEffect } from 'react';
import type { Theme, Density, Accent } from '../types';

const ACCENT_COLORS: Record<Accent, { brand: string; weak: string; ink: string }> = {
  green: { brand: 'oklch(0.58 0.14 150)', weak: 'oklch(0.95 0.045 150)', ink: 'oklch(0.38 0.10 150)' },
  indigo: { brand: 'oklch(0.52 0.18 275)', weak: 'oklch(0.96 0.04 275)', ink: 'oklch(0.34 0.14 275)' },
  amber: { brand: 'oklch(0.70 0.17 75)', weak: 'oklch(0.96 0.05 85)', ink: 'oklch(0.44 0.12 75)' },
  slate: { brand: 'oklch(0.40 0.020 265)', weak: 'oklch(0.95 0.005 265)', ink: 'oklch(0.22 0.012 265)' },
};

interface ThemeState {
  theme: Theme;
  density: Density;
  accent: Accent;
}

const DEFAULTS: ThemeState = {
  theme: 'light',
  density: 'compact',
  accent: 'slate',
};

export function useTheme() {
  const [state, setState] = useState<ThemeState>(DEFAULTS);

  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', state.theme);
    if (state.theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    document.body.className = state.density === 'compact' ? 'density-compact' : '';

    const accentColors = ACCENT_COLORS[state.accent];
    root.style.setProperty(`--accent-${state.accent}-brand`, accentColors.brand);
    root.style.setProperty(`--accent-${state.accent}-weak`, accentColors.weak);
    root.style.setProperty(`--accent-${state.accent}-ink`, accentColors.ink);
    root.style.setProperty('--primary', accentColors.brand);
    root.style.setProperty('--ring', accentColors.brand);
  }, [state]);

  return {
    ...state,
    setTheme: (theme: Theme) => setState(s => ({ ...s, theme })),
    setDensity: (density: Density) => setState(s => ({ ...s, density })),
    setAccent: (accent: Accent) => setState(s => ({ ...s, accent })),
  };
}
