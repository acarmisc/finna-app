// Shared components — pixel-art corporate style.
const { useState, useEffect, useRef, useMemo } = React;

// ------- Icon (lucide inline) -------
function Icon({ name, size=14, stroke=1.5, ...rest }) {
  return <i data-lucide={name} style={{width: size, height: size, strokeWidth: stroke}} {...rest} />;
}

// ------- Provider Badge -------
function ProviderBadge({ p, size='sm' }) {
  const label = { azure:'AZ', gcp:'GCP', llm:'LLM', aws:'AWS', ecb:'FX' }[p] || p?.toUpperCase().slice(0,2);
  const cls = ['llm','ecb'].includes(p) ? p : p;
  return <span className={`prov ${size==='lg' ? 'prov-lg' : ''} ${p==='ecb'?'':cls}`} style={p==='ecb'?{background:'var(--fg-muted)'}:{}}>{label}</span>;
}

// ------- Status Badge (handles status + severity + ok/err/warn) -------
const BADGE_MAP = {
  // run statuses
  started:   { cls:'solid-warning', text:'started' },
  running:   { cls:'solid-accent',  text:'running', pulse:true },
  completed: { cls:'ghost-accent',  text:'completed' },
  failed:    { cls:'ghost-danger',  text:'failed' },
  cancelled: { cls:'ghost-muted',   text:'cancelled' },
  // connection tests
  ok:   { cls:'ghost-accent',  text:'ok' },
  err:  { cls:'ghost-danger',  text:'error' },
  warn: { cls:'ghost-warning', text:'warn' },
  // alerts
  firing:   { cls:'solid-danger',  text:'firing', pulse:true },
  ack:      { cls:'ghost-warning', text:"ack'd" },
  resolved: { cls:'ghost-accent',  text:'resolved' },
  // severities
  critical: { cls:'solid-danger',  text:'critical' },
  warning:  { cls:'solid-warning', text:'warning' },
  info:     { cls:'ghost-primary', text:'info' },
};

function StatusBadge({ status }) {
  const m = BADGE_MAP[status] || { cls:'ghost-muted', text: status };
  return (
    <span className={`badge ${m.cls}`}>
      {m.pulse && <span className="dot pulse" />}
      {m.text}
    </span>
  );
}

// SeverityBadge kept as alias for backwards-compatibility with existing JSX.
const SeverityBadge = ({ severity }) => <StatusBadge status={severity} />;

// ------- Button with bracket flavor -------
function Button({ variant='default', size='md', icon, iconRight, bracket=false, children, onClick, disabled, type='button', block=false, ...rest }) {
  const cls = `btn btn-${variant} ${size!=='md' ? 'btn-'+size : ''} ${block?'btn-block':''}`;
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled} {...rest}>
      {icon && <Icon name={icon} />}
      {bracket && <span className="brackets-l">[</span>}
      <span>{children}</span>
      {bracket && <span className="brackets-r">]</span>}
      {iconRight && <Icon name={iconRight} />}
    </button>
  );
}

// ------- Stat Card -------
function StatCard({ label, value, unit='USD', delta, deltaDir='flat', meta, accent='primary', loading=false }) {
  if (loading) {
    return (
      <div className={`stat ${accent}`}>
        <div className="stat-lbl">{label}</div>
        <div className="skel" style={{width:'60%', height:28, marginTop:4}}/>
        <div className="skel" style={{width:'40%', height:12, marginTop:10}}/>
      </div>
    );
  }
  return (
    <div className={`stat ${accent}`}>
      <div className="stat-lbl">{label}</div>
      <div className="stat-val">
        {value}
        {unit && <span className="ccy">{unit}</span>}
      </div>
      {(delta || meta) && (
        <div className="stat-meta">
          {delta && <span className={`delta ${deltaDir}`}>{deltaDir==='up'?'▲':deltaDir==='down'?'▼':'—'} {delta}</span>}
          {meta && <span>· {meta}</span>}
        </div>
      )}
    </div>
  );
}

// ------- Progress Bar -------
function ProgressBar({ value, max=100, size='sm', stepped=false, segments=10 }) {
  const pct = Math.min(100, Math.max(0, (value/max)*100));
  const tone = pct >= 90 ? 'danger' : pct >= 70 ? 'warn' : '';
  if (stepped) {
    const filled = Math.round((pct/100) * segments);
    return (
      <div className={`pbar-steps ${tone}`}>
        {Array.from({length: segments}).map((_, i) => (
          <span key={i} className={`seg ${i < filled ? 'on' : ''}`} />
        ))}
      </div>
    );
  }
  return (
    <div className={`pbar ${size==='lg'?'pbar-lg':''} ${tone}`}>
      <div className="fill" style={{width: `${pct}%`}} />
    </div>
  );
}

// ------- CostDeltaCell -------
function CostDelta({ value, showArrow=true }) {
  if (value == null || isNaN(value)) return <span className="delta-flat">—</span>;
  const dir = value > 0.1 ? 'up' : value < -0.1 ? 'down' : 'flat';
  const arrow = dir==='up' ? '▲' : dir==='down' ? '▼' : '—';
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  return (
    <span className={`delta-${dir} mono num`}>
      {showArrow && <span style={{marginRight:4}}>{arrow}</span>}
      {sign}{Math.abs(value).toFixed(1)}%
    </span>
  );
}

// ------- Money format -------
function money(n, decimals=2) {
  if (n == null || isNaN(n)) return '—';
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}
function moneyShort(n) {
  if (n == null || isNaN(n)) return '—';
  if (Math.abs(n) >= 1e6) return '$' + (n/1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return '$' + (n/1e3).toFixed(1) + 'K';
  return '$' + n.toFixed(0);
}

// ------- Empty State -------
function EmptyState({ icon='inbox', title, message, action }) {
  return (
    <div className="empty">
      <div className="icon"><Icon name={icon} size={20}/></div>
      {title && <div style={{color:'var(--fg)', fontFamily:'JetBrains Mono, monospace', fontSize:13, marginBottom:4}}>{title}</div>}
      <div className="msg">{message}</div>
      {action && <div style={{marginTop:16}}>{action}</div>}
    </div>
  );
}

// ------- Toasts -------
const ToastCtx = React.createContext({ push: () => {} });
function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = (tone, msg) => {
    const id = Math.random().toString(36).slice(2);
    setItems(xs => [...xs, { id, tone, msg }]);
    setTimeout(() => setItems(xs => xs.filter(t => t.id !== id)), 4200);
  };
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="toasts">
        {items.map(t => (
          <div key={t.id} className={`toast ${t.tone}`}>
            <Icon name={t.tone==='ok'?'check-circle-2':t.tone==='err'?'x-circle':t.tone==='warn'?'alert-triangle':'info'} size={14}/>
            <span>{t.msg}</span>
            <span className="close" onClick={() => setItems(xs => xs.filter(x => x.id !== t.id))}>×</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
function useToast() { return React.useContext(ToastCtx); }

// ------- Dialog -------
function Dialog({ open, onClose, title, children, actions }) {
  if (!open) return null;
  return (
    <div className="dlg-scrim" onClick={onClose}>
      <div className="dlg" onClick={e => e.stopPropagation()}>
        <div className="dlg-hd">{title}</div>
        <div className="dlg-bd">{children}</div>
        <div className="dlg-ft">{actions}</div>
      </div>
    </div>
  );
}

// ------- SVG Line Chart -------
function LineChart({ series, width=700, height=220, showLegend=true, stacked=false }) {
  const pad = { l: 48, r: 12, t: 12, b: 28 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const allVals = series.flatMap(s => s.data.map(d => d.value));
  const maxVal = stacked
    ? Math.max(...series[0].data.map((_, i) => series.reduce((s, ser) => s + ser.data[i].value, 0)))
    : Math.max(...allVals);
  const max = Math.ceil(maxVal * 1.1 / 50) * 50;
  const len = series[0].data.length;
  const x = i => pad.l + (i / (len - 1)) * w;
  const y = v => pad.t + h - (v / max) * h;

  // Y ticks
  const ticks = [0, max*0.25, max*0.5, max*0.75, max];

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} style={{width:'100%', height:'auto', display:'block'}}>
        {/* grid */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} x2={pad.l+w} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeDasharray="2 3" />
            <text x={pad.l-8} y={y(t)+3} fill="var(--fg-subtle)" fontSize="10" fontFamily="JetBrains Mono, monospace" textAnchor="end">${t.toFixed(0)}</text>
          </g>
        ))}
        {/* x labels */}
        {series[0].data.map((d, i) => (
          (i % Math.ceil(len/8) === 0 || i === len-1) && (
            <text key={i} x={x(i)} y={pad.t+h+16} fill="var(--fg-subtle)" fontSize="10" fontFamily="JetBrains Mono, monospace" textAnchor="middle">{d.label}</text>
          )
        ))}
        {/* lines */}
        {series.map((ser, si) => {
          const pts = ser.data.map((d, i) => `${x(i)},${y(d.value)}`).join(' ');
          return (
            <g key={ser.name}>
              <polyline points={pts} fill="none" stroke={ser.color} strokeWidth="2" strokeLinejoin="miter" />
              {ser.data.map((d, i) => i % 3 === 0 && (
                <rect key={i} x={x(i)-2} y={y(d.value)-2} width="4" height="4" fill={ser.color} />
              ))}
            </g>
          );
        })}
        {/* frame */}
        <rect x={pad.l} y={pad.t} width={w} height={h} fill="none" stroke="var(--border)" />
      </svg>
      {showLegend && (
        <div className="chart-legend">
          {series.map(s => (
            <span key={s.name}><span className="swatch" style={{background:s.color}}/>{s.name}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ------- SVG stacked area / bar chart -------
function StackedAreaChart({ series, width=900, height=280 }) {
  const pad = { l: 56, r: 12, t: 12, b: 28 };
  const w = width - pad.l - pad.r;
  const h = height - pad.t - pad.b;
  const len = series[0].data.length;
  const totals = series[0].data.map((_, i) => series.reduce((s, ser) => s + ser.data[i].value, 0));
  const max = Math.ceil(Math.max(...totals) * 1.15 / 50) * 50;
  const x = i => pad.l + (i / (len - 1)) * w;
  const y = v => pad.t + h - (v / max) * h;
  const ticks = [0, max*0.25, max*0.5, max*0.75, max];

  // Build stacked polygons
  const stacked = [];
  let lowers = new Array(len).fill(0);
  for (const ser of series) {
    const uppers = ser.data.map((d, i) => lowers[i] + d.value);
    const top = uppers.map((v, i) => `${x(i)},${y(v)}`);
    const bottom = lowers.map((v, i) => `${x(i)},${y(v)}`).reverse();
    stacked.push({ color: ser.color, name: ser.name, path: [...top, ...bottom].join(' '), uppers });
    lowers = uppers;
  }

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} style={{width:'100%', height:'auto', display:'block'}}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} x2={pad.l+w} y1={y(t)} y2={y(t)} stroke="var(--border)" strokeDasharray="2 3" />
            <text x={pad.l-8} y={y(t)+3} fill="var(--fg-subtle)" fontSize="10" fontFamily="JetBrains Mono, monospace" textAnchor="end">${t.toFixed(0)}</text>
          </g>
        ))}
        {series[0].data.map((d, i) => (
          (i % Math.ceil(len/10) === 0 || i === len-1) && (
            <text key={i} x={x(i)} y={pad.t+h+16} fill="var(--fg-subtle)" fontSize="10" fontFamily="JetBrains Mono, monospace" textAnchor="middle">{d.label}</text>
          )
        ))}
        {stacked.map((s, i) => (
          <polygon key={i} points={s.path} fill={s.color} fillOpacity="0.7" stroke={s.color} strokeWidth="1" />
        ))}
        <rect x={pad.l} y={pad.t} width={w} height={h} fill="none" stroke="var(--border)" />
      </svg>
      <div className="chart-legend">
        {series.map(s => (
          <span key={s.name}><span className="swatch" style={{background:s.color}}/>{s.name}</span>
        ))}
      </div>
    </div>
  );
}

// ------- Horizontal bar list -------
function HBarList({ items, max, colorFor }) {
  const m = max ?? Math.max(...items.map(i => i.value));
  return (
    <div className="stack" style={{gap:10}}>
      {items.map((it, i) => (
        <div key={i} style={{display:'grid', gridTemplateColumns:'auto 1fr auto', gap:10, alignItems:'center', fontSize:12}}>
          <div style={{display:'flex', alignItems:'center', gap:8, minWidth:0, overflow:'hidden'}}>
            <ProviderBadge p={it.provider}/>
            <span className="mono truncate" style={{color:'var(--fg)'}}>{it.name}</span>
          </div>
          <div style={{position:'relative', height:8, background:'var(--surface-3)', border:'1px solid var(--border)'}}>
            <div style={{position:'absolute', left:0, top:0, bottom:0, width:`${(it.value/m)*100}%`, background: colorFor ? colorFor(it) : 'var(--primary)'}}/>
          </div>
          <div className="mono num" style={{color:'var(--fg)', minWidth:80, textAlign:'right'}}>{money(it.value)}</div>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, {
  Icon, ProviderBadge, StatusBadge, SeverityBadge, Button, StatCard, ProgressBar,
  CostDelta, EmptyState, ToastProvider, useToast, Dialog, LineChart, StackedAreaChart,
  HBarList, money, moneyShort,
});
