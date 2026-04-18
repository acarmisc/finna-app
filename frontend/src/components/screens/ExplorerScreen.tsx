import React, { useState, useMemo } from 'react';
import { TopBar } from '../common/TopBar';
import { Button } from '../common/Button';
import { ProviderTag } from '../common/ProviderTag';
import { Icon } from '../common/Icon';
import { FINNA_DATA } from '../../data';
import { fmt } from '../../utils/fmt';
import type { Toast, CostRecord } from '../../types';

interface ExplorerScreenProps {
  pushToast: (toast: Omit<Toast, 'id'>) => void;
  onOpenCost: (cost: CostRecord) => void;
}

export function ExplorerScreen({ pushToast, onOpenCost }: ExplorerScreenProps) {
  const { COSTS } = FINNA_DATA;
  const [q, setQ] = useState('');
  const [prov, setProv] = useState('all');
  const [sort, setSort] = useState<{ key: keyof CostRecord; dir: 'asc' | 'desc' }>({ key: 'mtd', dir: 'desc' });

  const rows = useMemo(() => {
    let r = COSTS.filter(c =>
      (prov === 'all' || c.prov === prov) &&
      (q === '' || c.name.toLowerCase().includes(q.toLowerCase()) || c.sku.toLowerCase().includes(q.toLowerCase()))
    );
    return [...r].sort((a, b) => {
      const mul = sort.dir === 'asc' ? 1 : -1;
      return (a[sort.key] > b[sort.key] ? 1 : -1) * mul;
    });
  }, [q, prov, sort, COSTS]);

  const total = rows.reduce((a, r) => a + r.mtd, 0);

  const SortHead = ({ k, children, num }: { k: keyof CostRecord; children: React.ReactNode; num?: boolean }) => (
    <th className={num ? 'num' : ''} onClick={() => setSort(s => ({ key: k, dir: s.key === k && s.dir === 'desc' ? 'asc' : 'desc' }))} style={{ cursor: 'pointer' }}>
      <span className="fn-th-inner">
        {children}
        {sort.key === k && <Icon name={sort.dir === 'desc' ? 'chevron-down' : 'chevron-up'} size={11} />}
      </span>
    </th>
  );

  return (
    <div className="fn-screen" data-screen-label="Cost explorer">
      <TopBar title="Cost explorer"
        subtitle={`${rows.length} rows · ${fmt.money(total)} matched`}
        actions={<>
          <Button variant="outline" size="sm" icon="filter">Saved views</Button>
          <Button variant="outline" size="sm" icon="share-2">Share</Button>
          <Button variant="primary" size="sm" icon="download"
            onClick={() => pushToast({ tone: 'ok', title: 'CSV exported', body: `${rows.length} rows · cost_records.csv` })}>
            Export CSV
          </Button>
        </>}
      />

      <div className="fn-filter-bar">
        <div className="fn-inp-wrap">
          <Icon name="search" size={14} className="fn-inp-icon" />
          <input className="fn-inp" placeholder="Filter by project, SKU, provider…" value={q} onChange={e => setQ(e.target.value)} />
          {q && <button className="fn-iconbtn" onClick={() => setQ('')}><Icon name="x" size={12} /></button>}
        </div>
        <div className="fn-seg">
          {(['all', 'gcp', 'azure', 'llm'] as const).map(p => (
            <button key={p} className={`fn-seg-btn ${prov === p ? 'is-active' : ''}`} onClick={() => setProv(p)}>
              {p === 'all' ? 'All' : p.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="fn-chips">
          <span className="fn-chip">Date: <b>Nov 1 – 14</b></span>
          <span className="fn-chip">Currency: <b>USD (ECB)</b></span>
          <span className="fn-chip">Granularity: <b>daily</b></span>
          <button className="fn-chip fn-chip-add"><Icon name="plus" size={10} /> Add filter</button>
        </div>
      </div>

      <div className="fn-panel fn-panel-flush">
        <table className="fn-table">
          <thead><tr>
            <SortHead k="prov">Provider</SortHead>
            <SortHead k="name">Project</SortHead>
            <SortHead k="sku">SKU</SortHead>
            <th className="num">Previous</th>
            <SortHead k="mtd" num>MTD · USD</SortHead>
            <SortHead k="delta" num>Δ</SortHead>
            <th></th>
          </tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="is-clickable" onClick={() => onOpenCost(r)}>
                <td style={{ width: 90 }}><ProviderTag p={r.prov} /></td>
                <td className="mono">{r.name}</td>
                <td>{r.sku}</td>
                <td className="num mono fn-muted">{fmt.money(r.prev)}</td>
                <td className="num mono fn-strong">{fmt.money(r.mtd)}</td>
                <td className={`num mono fn-${r.delta > 0 ? 'up' : r.delta < 0 ? 'down' : 'flat'}`}>{fmt.pct(r.delta)}</td>
                <td style={{ width: 28 }}><Icon name="chevron-right" size={14} style={{ color: 'var(--fg-subtle)' }} /></td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} className="fn-empty">No rows match your filters.</td></tr>
            )}
          </tbody>
          <tfoot><tr>
            <td colSpan={4} className="fn-foot-lbl">Total · {rows.length} rows</td>
            <td className="num mono fn-strong">{fmt.money(total)}</td>
            <td colSpan={2}></td>
          </tr></tfoot>
        </table>
      </div>
    </div>
  );
}
