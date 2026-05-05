# Graph Report - ui  (2026-05-04)

## Corpus Check
- 128 files · ~267,013 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 415 nodes · 477 edges · 22 communities detected
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4ec42dba`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 31|Community 31]]

## God Nodes (most connected - your core abstractions)
1. `APIClient` - 26 edges
2. `cn()` - 23 edges
3. `ProviderBadge()` - 14 edges
4. `Button()` - 12 edges
5. `StatusBadge()` - 11 edges
6. `useToast()` - 10 edges
7. `Icon()` - 9 edges
8. `money()` - 9 edges
9. `useTheme()` - 7 edges
10. `Input()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `App()` --calls--> `useTweaks()`  [INFERRED]
  design/wip/app.jsx → design/wip/tweaks-panel.jsx
- `ProtectedRoute()` --calls--> `useLocation()`  [INFERRED]
  src/components/layout/ProtectedRoute.tsx → src/__mocks__/react-router-dom.ts
- `DateRangeProvider()` --calls--> `useSearchParams()`  [INFERRED]
  src/contexts/DateRangeContext.tsx → src/__mocks__/react-router-dom.ts
- `useDateRangeParams()` --calls--> `useDateRange()`  [INFERRED]
  src/hooks/useDateRange.ts → src/contexts/DateRangeContext.tsx
- `useThemeHook()` --calls--> `useTheme()`  [INFERRED]
  src/hooks/useTheme.ts → src/contexts/ThemeContext.tsx

## Communities (78 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (8): NotificationToggle(), SettingsSection(), StatusBadge(), Input(), SelectContent(), SelectItem(), SelectTrigger(), SelectValue()

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (9): DateRangeProvider(), getRangeFromWindow(), useDateRange(), ThemeProvider(), useTheme(), ToastProvider(), useDateRangeParams(), useThemeHook() (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.27
Nodes (11): addSortIndicators(), enableUI(), getNthColumn(), getTable(), getTableBody(), getTableHeader(), loadColumns(), loadData() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.35
Nodes (8): a(), B(), D(), g(), i(), k(), Q(), y()

### Community 12 - "Community 12"
Cohesion: 0.2
Nodes (3): buildPayload(), submit(), Icon()

### Community 14 - "Community 14"
Cohesion: 0.24
Nodes (3): add(), onKey(), remove()

### Community 27 - "Community 27"
Cohesion: 0.7
Nodes (4): goToNext(), goToPrevious(), makeCurrent(), toggleClass()

## Knowledge Gaps
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `cn()` connect `Community 7` to `Community 0`, `Community 34`, `Community 35`, `Community 40`, `Community 41`, `Community 42`, `Community 9`, `Community 22`, `Community 23`, `Community 24`, `Community 28`, `Community 29`, `Community 31`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `ProviderBadge()` connect `Community 9` to `Community 0`, `Community 32`, `Community 12`, `Community 14`, `Community 16`, `Community 25`, `Community 26`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `StatusBadge()` connect `Community 0` to `Community 32`, `Community 14`, `Community 16`, `Community 18`, `Community 26`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._