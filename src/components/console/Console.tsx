import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './Sidebar';
import { DashboardScreen } from '../screens/DashboardScreen';
import { ExplorerScreen } from '../screens/ExplorerScreen';
import { ConnectionsScreen } from '../screens/ConnectionsScreen';
import { AlertsScreen } from '../screens/AlertsScreen';
import { RunsScreen } from '../screens/RunsScreen';
import { BudgetsScreen } from '../screens/BudgetsScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { ProjectsScreen, ProjectDetailScreen } from '../screens/ProjectsScreen';
import { ConnectionDetailScreen } from '../screens/ConnectionDetailScreen';
import { ResourceDetailScreen } from '../screens/ResourceDetailScreen';
import { CommandPalette } from './CommandPalette';
import { NewConnectionModal } from '../modals/NewConnectionModal';
import { NewProjectModal } from '../modals/NewProjectModal';
import { NewResourceModal } from '../modals/NewResourceModal';
import { TagEditorModal } from '../modals/TagEditorModal';
import { MoveResourceModal } from '../modals/MoveResourceModal';
import { ConnectionDrawer } from '../drawers/ConnectionDrawer';
import { CostDrawer } from '../drawers/CostDrawer';
import { RunDrawer } from '../drawers/RunDrawer';
import { Toaster } from './Toaster';
import { TweaksPanel } from '../common/TweaksPanel';
import { useTheme } from '../../hooks/useTheme';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAppData } from '../../hooks/useAppData';
import type { Toast, Connection, CostRecord, Run, Route, Resource, FinProject } from '../../types';
import './Console.css';

const SCREENS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'gauge' },
  { id: 'explorer', label: 'Cost explorer', icon: 'chart-line' },
  { id: 'projects', label: 'Projects', icon: 'folder-tree' },
  { id: 'connections', label: 'Connections', icon: 'plug' },
  { id: 'alerts', label: 'Alerts', icon: 'bell' },
  { id: 'runs', label: 'Run log', icon: 'database' },
  { id: 'budgets', label: 'Budgets', icon: 'wallet' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
];

export function Console() {
  const [route, setRoute] = useLocalStorage<Route>('finna-route', { screen: 'dashboard' });
  const [collapsed, setCollapsed] = useLocalStorage('finna-collapsed', false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [newConn, setNewConn] = useState(false);
  const [newConnForProject, setNewConnForProject] = useState<string | null>(null);
  const [newProject, setNewProject] = useState(false);
  const [newResource, setNewResource] = useState(false);
  const [newResourceConn, setNewResourceConn] = useState<Connection | null>(null);
  const [tagTarget, setTagTarget] = useState<{ name: string; tags: Record<string, string> } | null>(null);
  const [moveResource, setMoveResource] = useState<Resource | null>(null);
  const [moveFromConn, setMoveFromConn] = useState<string | null>(null);
  const [drawerConn, setDrawerConn] = useState<Connection | null>(null);
  const [drawerCost, setDrawerCost] = useState<CostRecord | null>(null);
  const [drawerRun, setDrawerRun] = useState<Run | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [tweaksOpen, setTweaksOpen] = useState(false);
  const { theme, accent, density, setTheme, setAccent, setDensity } = useTheme();
  const { data: FINNA_DATA } = useAppData();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCmdOpen(o => !o);
      }
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === 't') {
        e.preventDefault();
        setTweaksOpen(o => !o);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const pushToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2, 8);
    setToasts(ts => [...ts, { id, ...toast }]);
    setTimeout(() => setToasts(ts => ts.filter(t => t.id !== id)), 4500);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(ts => ts.filter(t => t.id !== id));
  }, []);

  const handleOpenConnection = useCallback((connId: string) => {
    setRoute({ screen: 'connection', connectionId: connId });
  }, []);

  const handleOpenResource = useCallback((connId: string, resId: string) => {
    setRoute({ screen: 'resource', connectionId: connId, resourceId: resId });
  }, []);

  const handleNewResource = useCallback(() => {
    if (route.screen === 'connection') {
      const conn = FINNA_DATA.CONNECTIONS.find(c => c.id === (route as any).connectionId) || null;
      setNewResourceConn(conn);
    }
    setNewResource(true);
  }, [route]);

  const currentScreen = route.screen;

  let screenEl: React.ReactNode;
  switch (route.screen) {
    case 'explorer':
      screenEl = <ExplorerScreen pushToast={pushToast} onOpenCost={setDrawerCost} />;
      break;
    case 'connections':
      screenEl = (
        <ConnectionsScreen
          pushToast={pushToast}
          onNew={() => setNewConn(true)}
          onOpen={c => setRoute({ screen: 'connection', connectionId: c.id })}
          onNav={setRoute}
        />
      );
      break;
    case 'projects':
      screenEl = (
        <ProjectsScreen
          pushToast={pushToast}
          onOpenProject={id => setRoute({ screen: 'project', projectId: id })}
          onNewProject={() => setNewProject(true)}
        />
      );
      break;
    case 'project':
      screenEl = (
        <ProjectDetailScreen
          projectId={route.projectId}
          onNav={setRoute}
          onOpenConnection={handleOpenConnection}
          pushToast={pushToast}
          onNewConnection={pid => { setNewConnForProject(pid); setNewConn(true); }}
        />
      );
      break;
    case 'connection':
      screenEl = (
        <ConnectionDetailScreen
          connectionId={route.connectionId}
          onNav={setRoute}
          onOpenResource={handleOpenResource}
          pushToast={pushToast}
          onNewResource={handleNewResource}
        />
      );
      break;
    case 'resource':
      screenEl = (
        <ResourceDetailScreen
          connectionId={route.connectionId}
          resourceId={route.resourceId}
          onNav={setRoute}
          pushToast={pushToast}
          onEditTags={() => {
            const c = FINNA_DATA.CONNECTIONS.find(x => x.id === (route as any).connectionId);
            const r = c?.resources?.find(x => x.id === (route as any).resourceId);
            if (r) setTagTarget({ name: r.name, tags: r.tags });
          }}
          onMoveResource={() => {
            const c = FINNA_DATA.CONNECTIONS.find(x => x.id === (route as any).connectionId);
            const r = c?.resources?.find(x => x.id === (route as any).resourceId);
            if (r) { setMoveResource(r); setMoveFromConn((route as any).connectionId); }
          }}
        />
      );
      break;
    case 'alerts':
      screenEl = <AlertsScreen pushToast={pushToast} />;
      break;
    case 'runs':
      screenEl = <RunsScreen onOpenRun={setDrawerRun} />;
      break;
    case 'budgets':
      screenEl = <BudgetsScreen />;
      break;
    case 'settings':
      screenEl = <SettingsScreen />;
      break;
    default:
      screenEl = <DashboardScreen pushToast={pushToast} />;
  }

  return (
    <div
      className={`fn-app ${collapsed ? 'is-collapsed' : ''}`}
      data-theme={theme}
      data-density={density === 'compact' ? 'compact' : 'cozy'}
      style={{
        '--accent-brand': `var(--accent-${accent}-brand)`,
        '--accent-weak': `var(--accent-${accent}-weak)`,
        '--accent-ink': `var(--accent-${accent}-ink)`,
      } as React.CSSProperties}
    >
      <Sidebar
        current={currentScreen}
        onNav={setRoute}
        onOpenCmd={() => setCmdOpen(true)}
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
      />
      <main className="fn-main">{screenEl}</main>

      <NewConnectionModal
        open={newConn}
        onClose={() => { setNewConn(false); setNewConnForProject(null); }}
        onCreate={c => {
          pushToast({ tone: 'ok', title: `Created ${c.name}`, body: `${c.provider.toUpperCase()} · dry-run scheduled` });
        }}
      />
      <NewProjectModal
        open={newProject}
        onClose={() => setNewProject(false)}
        onCreate={p => pushToast({ tone: 'ok', title: `Created project ${p.name}` })}
      />
      <NewResourceModal
        open={newResource}
        onClose={() => setNewResource(false)}
        connection={newResourceConn}
        onCreate={r => pushToast({ tone: 'ok', title: `Added resource ${r.name}` })}
      />
      <TagEditorModal
        open={!!tagTarget}
        onClose={() => setTagTarget(null)}
        target={tagTarget}
        onSave={() => pushToast({ tone: 'ok', title: 'Tags saved', body: 'Back-fill queued for nightly run.' })}
      />
      <MoveResourceModal
        open={!!moveResource}
        onClose={() => { setMoveResource(null); setMoveFromConn(null); }}
        resource={moveResource}
        currentConnectionId={moveFromConn}
        onMove={dest => pushToast({ tone: 'ok', title: `Moved ${moveResource?.name}`, body: `Destination: ${dest}` })}
      />
      <ConnectionDrawer c={drawerConn} onClose={() => setDrawerConn(null)} pushToast={pushToast} />
      <CostDrawer row={drawerCost} onClose={() => setDrawerCost(null)} />
      <RunDrawer run={drawerRun} onClose={() => setDrawerRun(null)} />
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} onNav={id => setRoute({ screen: id } as Route)} screens={SCREENS} />
      <TweaksPanel
        open={tweaksOpen}
        onClose={() => setTweaksOpen(false)}
        theme={theme}
        density={density}
        accent={accent}
        setTheme={setTheme}
        setDensity={setDensity}
        setAccent={setAccent}
      />
      <Toaster toasts={toasts} dismiss={dismissToast} />
    </div>
  );
}
