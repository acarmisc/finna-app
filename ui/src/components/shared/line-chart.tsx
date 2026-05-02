import React from 'react'

interface LineChartProps {
  series: Array<{
    name: string
    color: string
    data: Array<{ label: string; value: number }>
  }>
  width?: number
  height?: number
  showLegend?: boolean
  stacked?: boolean
}

export function LineChart({
  series,
  width = 700,
  height = 220,
  showLegend = true,
  stacked = false,
}: LineChartProps) {
  const pad = { l: 48, r: 12, t: 12, b: 28 }
  const w = width - pad.l - pad.r
  const h = height - pad.t - pad.b

  const allVals = series.flatMap(s => s.data.map(d => d.value))
  const maxVal = stacked
    ? Math.max(...series[0].data.map((_, i) =>
        series.reduce((s, ser) => s + ser.data[i].value, 0)
      ))
    : Math.max(...allVals)
  const max = Math.ceil(maxVal * 1.1 / 50) * 50
  const len = series[0]?.data.length || 0

  const x = (i: number) => pad.l + (i / Math.max(len - 1, 1)) * w
  const y = (v: number) => pad.t + h - (v / max) * h

  const ticks = [0, max * 0.25, max * 0.5, max * 0.75, max]

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
          (i % Math.ceil(len / 8) === 0 || i === len - 1) && (
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

        {/* lines */}
        {series.map((ser, si) => {
          const pts = ser.data.map((d, i) => `${x(i).toFixed(1)},${y(d.value).toFixed(1)}`).join(' ')
          return (
            <g key={ser.name}>
              <polyline
                points={pts}
                fill="none"
                stroke={ser.color}
                strokeWidth="2"
                strokeLinejoin="miter"
              />
              {ser.data.map((d, i) =>
                i % 3 === 0 && (
                  <rect
                    key={i}
                    x={x(i) - 2}
                    y={y(d.value) - 2}
                    width="4"
                    height="4"
                    fill={ser.color}
                  />
                )
              )}
            </g>
          )
        })}

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
      {showLegend && (
        <div className="chart-legend">
          {series.map(s => (
            <span key={s.name}>
              <span className="swatch" style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default LineChart