import React from 'react'

// Inline SVG icon component (no external icon library dependency)
// Maps icon names to SVG paths
const ICONS: Record<string, string> = {
  'check-circle-2': 'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm-1.5 6.5 4 4-4 4-1-1 3-3-3-3 1-1z',
  'x-circle': 'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm3.5 6.5-2.8 2.8-2.8-2.8-1.4 1.4 2.8 2.8-2.8 2.8 1.4 1.4 2.8-2.8 2.8 2.8 1.4-1.4-2.8-2.8 2.8-2.8-1.4-1.4z',
  'alert-triangle': 'M12 2L2 20h20L12 2zm0 3v6m0 4v.01',
  'info': 'M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 5v6m0 4v.01',
  'check': 'M9 12l2 2 4-4m6 2a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  'x': 'M18 6L6 18M6 6l12 12',
  'plus': 'M12 5v14M5 12h14',
  'minus': 'M5 12h14',
  'edit-3': 'M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z',
  'trash-2': 'M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2',
  'search': 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10z',
  'search-x': 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-3 5v2m4-2v2m-6 2h12',
  'refresh-ccw': 'M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15',
  'download': 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  'layout-grid': 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  'activity': 'M22 12h-4l-3 9L9 3l-3 9H2',
  'play': 'M5 3l14 9-14 9V3z',
  'loader': 'M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83',
  'calendar': 'M19 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zM16 2v4M8 2v4M3 10h18',
  'inbox': 'M22 12h-6l-2 3H10l-2-3H2M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z',
  'chevron-down': 'M6 9l6 6 6-6',
  'chevron-up': 'M18 15l-6-6-6 6',
  'chevron-right': 'M9 18l6-6-6-6',
  'more-horizontal': 'M12 12h.01M19 12h.01M5 12h.01',
  'layout-dashboard': 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  'chart-line': 'M3 3v18h18M7 16l4-4 4 4 5-6',
  'folders': 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v11z',
  'plug': 'M7 22V2h10v20M12 12h.01M5 12h14',
  'database': 'M12 2C6.48 2 2 4.69 2 8v8c0 3.31 4.48 6 10 6s10-2.69 10-6V8c0-3.31-4.48-6-10-6zM12 12c-2.21 0-4-1.57-4-3.5S9.79 5 12 5s4 1.57 4 3.5S14.21 12 12 12z',
  'settings-2': 'M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16zm0-8l3 3m-3-3-3 3',
  'bell': 'M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0',
  'sun': 'M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12z',
  'moon': 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  'log-out': 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9',
  'upload': 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12',
  'filter': 'M22 3H2l8 9.46V19l4 2v-8.54L22 3z',
  'external-link': 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3',
}

interface IconProps {
  name: string
  size?: number
  stroke?: number
  className?: string
  style?: React.CSSProperties
}

export function Icon({ name, size = 14, stroke = 1.5, className, style }: IconProps) {
  const path = ICONS[name] || ICONS['info']
  const title = name.replace(/-/g, ' ')
  
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={className}
      style={style}
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <path d={path} />
    </svg>
  )
}

export default Icon