// Main entry point
const { useState: uSM, useEffect: uEM } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark"
}/*EDITMODE-END*/;

function App() {
  const route = useHashRoute();
  const [authed, setAuthed] = uSM(() => localStorage.getItem('finna_auth') === '1');
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [localTheme, setLocalTheme] = uSM(() => localStorage.getItem('finna_theme') || t.theme || 'dark');
  const theme = localTheme;

  uEM(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('finna_theme', theme);
  }, [theme]);

  uEM(() => { if (t.theme && t.theme !== localTheme) setLocalTheme(t.theme); }, [t.theme]);
  uEM(() => { if (window.lucide) window.lucide.createIcons(); });

  const setTheme = (v) => { setLocalTheme(v); setTweak('theme', v); };
  const doAuth = () => { localStorage.setItem('finna_auth','1'); setAuthed(true); navigate('/dashboard'); };
  const logout = () => { localStorage.removeItem('finna_auth'); setAuthed(false); navigate('/login'); };

  const tweaksPanel = (
    <TweaksPanel title="Tweaks">
      <TweakSection title="Theme">
        <TweakRadio label="Mode" value={theme} options={[{value:'dark',label:'Dark'},{value:'light',label:'Light'}]} onChange={setTheme}/>
      </TweakSection>
    </TweaksPanel>
  );

  if (!authed || route.base === '/login') {
    return (
      <ToastProvider>
        <LoginPage onAuth={doAuth}/>
        {tweaksPanel}
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <AppShell theme={theme} setTheme={setTheme} onLogout={logout}>
        {(r, ctx) => {
          const base = r.base;
          if (base === '/dashboard') return <DashboardPage range={ctx.range}/>;
          if (base === '/projects') {
            if (r.sub) return <ProjectDetailPage slug={r.sub}/>;
            return <ProjectsListPage/>;
          }
          if (base === '/configs') {
            if (r.sub === 'new') return <ConfigCreatePage/>;
            if (r.sub) return <ConfigCreatePage editId={r.sub}/>;
            return <ConfigsListPage/>;
          }
          if (base === '/extractors') return <ExtractorsPage/>;
          if (base === '/costs') return <CostsPage range={ctx.range}/>;
          if (base === '/alerts') return <AlertsPage/>;
          if (base === '/settings') return <SettingsPage/>;
          return <div className="page"><EmptyState icon="compass" title="Route not found" message={`no view for ${r.path}`} action={<Button bracket onClick={()=>navigate('/dashboard')}>go to dashboard</Button>}/></div>;
        }}
      </AppShell>
      {tweaksPanel}
    </ToastProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
