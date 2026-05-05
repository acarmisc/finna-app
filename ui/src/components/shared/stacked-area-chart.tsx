import React from 'react'

interface StackedAreaChartProps {
  series: Array<{
    name: string
    color: string
    data: Array<{ label: string; value: number }>
  }>
  width?: number
  height?: number
}

export function StackedAreaChart({
  series,
  width = 900,
  height = 280,
}: StackedAreaChartProps) {
  const pad = { l: 56, r: 12, t: 12, b: 28 }
  const w = width - pad.l - pad.r
  const h = height - pad.t - pad.b
  const len = series[0]?.data.length || 0

  const totals = series[0]?.data.map((_, i) =>
    series.reduce((s, ser) => s + ser.data[i].value, 0)
  ) || []
  const max = Math.ceil(Math.max(...totals, 1) * 1.15 / 50) * 50

  const x = (i: number) => pad.l + (i / Math.max(len - 1, 1)) * w
  const y = (v: number) => pad.t + h - (v / max) * h
  const ticks = [0, max * 0.25, max * 0.5, max * 0.75, max]

  // Build stacked polygons
  const stacked = []
  let lowers = new Array(len).fill(0)
  for (const ser of series) {
    const uppers = ser.data.map((d, i) => lowers[i] + d.value)
    const top = uppers.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`)
    const bottom = lowers.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).reverse()
    stacked.push({ color: ser.color, name: ser.name, path: [...top, ...bottom].join(' '), uppers })
    lowers = uppers
  }

  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
      >
        {/* grid */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={pad.l}
              x2={pad.l + w}
              y1={y(t)}
              y2={y(t)}
              stroke="var(--border)"
              strokeDasharray="2 3"
            />
            <text
              x={pad.l - 8}
              y={y(t) + 3}
              fill="var(--fg-subtle)"
              fontSize="10"
              fontFamily="JetBrains Mono, monospace"
              textAnchor="end"
            >
              ${t.toFixed(0)}
            </text>
          </g>
        ))}

        {/* x labels */}
        {series[0]?.data.map((d, i) => (
          (i % Math.ceil(len / 10) === 0 || i === len - 1) && (
            <text
              key={i}
              x={x(i)}
              y={pad.t + h + 16}
              fill="var(--fg-subtle)"
              fontSize="10"
              fontFamily="JetBrains Mono, monospace"
              textAnchor="middle"
            >
              {d.label}
            </text>
          )
        ))}

        {/* stacked areas */}
        {stacked.map((s, i) => (
          <polygon
            key={i}
            points={s.path}
            fill={s.color}
            fillOpacity="0.7"
            stroke={s.color}
            strokeWidth="1"
          />
        ))}

        {/* frame */}
        <rect
          x={pad.l}
          y={pad.t}
          width={w}
          height={h}
          fill="none"
          stroke="var(--border)"
        />
      </svg>
      <div className="chart-legend">
        {series.map(s => (
          <span key={s.name}>
            <span className="swatch" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  )
}

export default StackedAreaChart