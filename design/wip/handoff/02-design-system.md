# 02 · Design system

The visual language is **pixel-art corporate** — sharp corners (radius 0), 1px solid borders everywhere, chunky pixel-step shadows (no blur), Press Start 2P for titles only, JetBrains Mono for numbers/IDs/buttons, Inter for body and prose. Read this doc before writing any UI — every component below depends on these tokens.

## Tokens

Defined as CSS custom properties at `:root` (dark) and overridden under `[data-theme="light"]`.

### Surface / text

```
--bg          page background
--surface     primary container
--surface-2   table head, card head, hover row
--surface-3   pressed / extra elevation
--border      1px container border
--border-2    subtle inner divider (table rows)
--fg          body text
--fg-muted    secondary text
--fg-subtle   tertiary / placeholder
```

### Brand / semantic

```
--primary       brand action (blue dark / blue light)
--primary-fg    text-on-primary
--accent        success / running (green)
--warning       soft caution (yellow)
--danger        critical / destructive / cost-rising (red)
--info          link / info-blue
```

### Provider colors (use ONLY on provider tags)

```
--azure  #0078d4
--gcp    #ea4335
--llm    #7c3aed
--aws    #ff9900
```

### Pixel-art layer

```
--pxshadow-1   2px 2px 0 0 rgba(0,0,0,0.6)   small (chips, badges)
--pxshadow-2   4px 4px 0 0 rgba(0,0,0,0.55)  medium (cards, stat tiles)
--pxshadow-3   6px 6px 0 0 rgba(0,0,0,0.5)   dialog
--pxshadow-primary, --pxshadow-danger        button variants
```

## Typography

| Surface | Family | Size / weight |
|---|---|---|
| Body / chrome | Inter | 13.5px / 400 |
| Page H1 (`.page-head h1`) | **Press Start 2P** | 16px / 400, no `text-transform` |
| Card title (`.card-hd h3`) | Inter | 13px / 600 |
| Stat value (`.stat-val`) | JetBrains Mono | 26px / 600, tabular-nums |
| Stat label (`.stat-lbl`) | JetBrains Mono | 11px / 500 uppercase |
| Button label | JetBrains Mono | 12px / 500 (uppercased when `bracket`) |
| Badges (status / severity / provider) | JetBrains Mono | 10px / 600 uppercase |
| IDs / paths / numbers in tables | JetBrains Mono | inherits |
| `// hint` (terminal-style) | JetBrains Mono | 12-13px |
| Login headline | Press Start 2P | 22px / 400 |
| Logo wordmark (`.sb-logo .wm`) | Press Start 2P | 11px |
| Steps wizard step label | Press Start 2P | 8px |
| Empty-state title (`.empty h3`) | Press Start 2P | 11px |
| Dialog header (`.dialog-hd`) | Press Start 2P | 10px |
| Table head (`.tbl th`) | Inter | 11px / 600 (NOT mono) |

**Rule of thumb**: titles use Press Start 2P; numbers/IDs/buttons use JetBrains Mono; everything else is Inter. Never use Press Start 2P for body or for stat values.

## Tailwind v4 wiring

`src/styles/tokens.css`: copy the `:root { … }` and `[data-theme="light"] { … }` blocks from the mockup's `styles.css`.

`src/styles/index.css`:

```css
@import 'tailwindcss';
@import './tokens.css';
@import './pixel-art.css';

@theme {
  --color-bg:        var(--bg);
  --color-surface:   var(--surface);
  --color-surface-2: var(--surface-2);
  --color-surface-3: var(--surface-3);
  --color-border:    var(--border);
  --color-fg:        var(--fg);
  --color-fg-muted:  var(--fg-muted);
  --color-fg-subtle: var(--fg-subtle);
  --color-primary:   var(--primary);
  --color-accent:    var(--accent);
  --color-warning:   var(--warning);
  --color-danger:    var(--danger);
  --color-azure:     var(--azure);
  --color-gcp:       var(--gcp);
  --color-llm:       var(--llm);

  --font-sans:   'Inter', system-ui, sans-serif;
  --font-mono:   'JetBrains Mono', ui-monospace, monospace;
  --font-pixel:  'Press Start 2P', monospace;

  --radius: 0;
}

html { font-family: var(--font-sans); }
```

Load fonts in `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet"
  href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Press+Start+2P&display=swap" />
```

## Shadows / shape

- **Border radius is 0**. Never round.
- **Borders**: `1px solid var(--border)` on containers, inputs, badges, table cells. Sidebar/topbar use 2px.
- **Shadows are pixel-step** (no blur). Define via `--pxshadow-*`. Hover may grow a step; press drops to none.
- **Hover**: 60-80ms `steps(2)` transitions. Buttons translate `(-1px,-1px)` and gain shadow; press translates `(2px,2px)` and drops shadow.
- **Focus**: 2px solid primary outline with 0 offset. No glow.

## Color usage rules

- `--primary` — primary actions, accents, active sidebar items.
- Provider colors — provider tags only. Never decorative.
- `--accent` — success, running, "ok".
- `--warning` — soft caution.
- `--danger` — destructive actions, critical alerts, **rising cost deltas** (cost going up = bad).
- `--surface-2` / `--surface-3` — subtle elevation, table headers, hover.

## Components catalogue

Full props in `components.jsx`. Cross-reference when building shadcn replacements.

| Component | Replacement strategy |
|---|---|
| `Icon({name,size,stroke})` | Replace with `lucide-react` `<X size={14} />` imports. Drop the global `data-lucide` runtime. |
| `Button({variant,size,icon,iconRight,bracket,block,…})` | Extend shadcn `<Button>` via `cva`. Add `bracket` boolean: when true, prepend `[` + space and append space + `]`, force uppercase + mono, add pixel shadow. Variants: `default`, `primary`, `danger`, `ghost`. |
| `StatCard({label,value,unit,delta,deltaDir,meta,accent,loading})` | Custom component over shadcn `Card`. Left-rail accent stripe (`accent: primary\|azure\|gcp\|llm\|danger\|accent`). `loading=true` → skeleton matching final shape. |
| `ProviderBadge({p,size})` | Solid block, mono code (AZ / GCP / LLM / AWS / FX). Provider colors only. |
| `StatusBadge({status})` | Single source of truth (see `BADGE_MAP`). Handles run statuses, alert statuses, severities, ok/err/warn. Pulse dot for `running` and `firing`. |
| `SeverityBadge({severity})` | Thin alias for `StatusBadge` — kept for readability at call sites. |
| `ProgressBar({value,max,size,stepped,segments})` | Pixel-stitched bar. Tone (danger ≥90%, warn ≥70%, ok) auto-derived from pct. |
| `CostDelta({value,showArrow})` | ▲ red / ▼ green / — gray. Cost up = bad. |
| `EmptyState({icon,title,message,action})` | Inbox icon + title + mono `// hint` + optional action button. |
| `Dialog({open,onClose,title,children,actions})` | Replace with shadcn `<Dialog>` styled to match `.dialog-hd` (pixel header, primary fill stripe, square close × button). |
| `LineChart({series,…})` / `StackedAreaChart({…})` | **Replace with Recharts.** Disable animation, square line-caps, mono tick labels, dashed grid. See `02-design-system-charts.md` snippet below. |
| `HBarList({items,max,colorFor})` | Keep hand-rolled — simpler than Recharts for this use case. |
| `Sparkline({seed,up})` | Used on project cards. Replace with Recharts `<LineChart>` minimal config or keep custom SVG. |
| `ToastProvider`/`useToast()` | Replace with shadcn `useToast`. Tones: `ok`, `err`, `info`. |
| `money(n,decimals=2)` / `moneyShort(n)` | Pure helpers in `src/utils/money.ts`. |

### Recharts: `LineChart` replacement

```tsx
import { ResponsiveContainer, LineChart as RC, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';

export function LineChart({ series }: { series: Series[] }) {
  const flat = series[0].data.map((p, i) => {
    const row: any = { label: p.label };
    series.forEach(s => { row[s.name] = s.data[i].value; });
    return row;
  });
  return (
    <ResponsiveContainer width="100%" height={220}>
      <RC data={flat} margin={{ top: 12, right: 12, bottom: 28, left: 48 }}>
        <CartesianGrid stroke="var(--border)" strokeDasharray="2 3" vertical={false}/>
        <XAxis dataKey="label" tick={{ fontFamily: 'JetBrains Mono', fontSize: 10, fill: 'var(--fg-subtle)' }} stroke="var(--border)"/>
        <YAxis tickFormatter={moneyShort} tick={{ fontFamily: 'JetBrains Mono', fontSize: 10, fill: 'var(--fg-subtle)' }} stroke="var(--border)"/>
        <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 0, fontFamily: 'JetBrains Mono', fontSize: 11 }}/>
        <Legend wrapperStyle={{ fontFamily: 'JetBrains Mono', fontSize: 11 }}/>
        {series.map(s => (
          <Line key={s.name} type="monotone" dataKey={s.name} stroke={s.color} strokeWidth={1.5} dot={false} isAnimationActive={false}/>
        ))}
      </RC>
    </ResponsiveContainer>
  );
}
```

### `BracketButton` (shadcn extension)

```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 transition-[transform,box-shadow] duration-75 hover:-translate-x-px hover:-translate-y-px active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-surface text-fg border border-border hover:bg-surface-3 shadow-[2px_2px_0_0_rgb(0_0_0/0.6)]",
        primary: "bg-primary text-primary-fg border border-primary shadow-[2px_2px_0_0_rgb(0_0_0/0.4)]",
        danger:  "bg-danger text-white border border-danger shadow-[2px_2px_0_0_rgb(0_0_0/0.4)]",
        ghost:   "bg-transparent border-transparent hover:bg-surface-2 shadow-none",
      },
      size: {
        sm: "h-7 px-2.5 text-[11px]",
        md: "h-8 px-3 text-[12px]",
        lg: "h-10 px-4 text-[13px]",
      },
      bracket: {
        true: "font-mono uppercase tracking-wide before:content-['['] before:mr-1 before:opacity-70 after:content-[']'] after:ml-1 after:opacity-70",
        false: "",
      },
    },
    defaultVariants: { variant: "default", size: "md", bracket: false },
  },
);
```

## Done when

- [ ] `src/styles/tokens.css` matches mockup `styles.css` (dark + light blocks).
- [ ] Press Start 2P + JetBrains Mono + Inter all loaded and visible on `/dashboard`.
- [ ] `<Button bracket>` renders `[ LABEL ]`-style mono uppercased.
- [ ] All cards have 1px border + pixel-step shadow + radius 0.
- [ ] `data-theme` toggle flips all token-driven styles atomically.
- [ ] Light theme passes WCAG AA on body text + badges.
