# 03 · Auth

OAuth2 / OIDC SSO + email-password fallback. JWT access tokens, refresh on 401. The mockup's `LoginPage` already renders the final visual — this doc wires the behaviour.

## SSO providers (mockup)

`pages-1.jsx` exports `SSO_PROVIDERS`:

| id | Label | Type | Notes |
|---|---|---|---|
| `google` | Continue with Google | OAuth | Brand SVG inline |
| `microsoft` | Continue with Microsoft | OAuth | Brand SVG inline |
| `okta` | Continue with Okta | SAML | Hosted at customer Okta tenant |
| `github` | Continue with GitHub | OAuth | Internal staff fallback |
| `saml` | SAML SSO | Enterprise | Generic SAML — tenant-config driven |

The list is hard-coded for the mockup. **In production**, fetch enabled providers from the backend so org admins can toggle them: `GET /auth/providers` → `[{ id, label, type, icon_url, sort_order }]`. Render whatever the API returns; the email-password form remains as fallback.

## Endpoints

```
GET  /auth/providers                  # which SSO buttons to show, per tenant
POST /auth/login                      # email + password → tokens
POST /auth/sso/{providerId}/start     # → { redirect_url, state }
GET  /auth/sso/{providerId}/callback  # backend handles, redirects to /auth/callback?code=…
POST /auth/refresh                    # refresh_token → new access_token
POST /auth/logout                     # revokes refresh_token server-side
GET  /users/me                        # current user (after auth)
```

`/auth/callback` on the frontend exchanges `?code=…` for tokens via `POST /auth/token/exchange`.

## Token storage

| Token | Stored | Lifetime |
|---|---|---|
| `access_token` | memory (Zustand store) + `sessionStorage` mirror | 15 min |
| `refresh_token` | **httpOnly cookie** set by the backend | 30 days, sliding |
| `csrf_token` | `localStorage` | matches refresh |

Never put refresh tokens in `localStorage` or non-httpOnly cookies. The frontend never reads `refresh_token` directly.

## axios client (`src/api/client.ts`)

```ts
import axios from 'axios';
import { useAuthStore } from '@/features/auth/store';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true, // send refresh cookie
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const csrf = localStorage.getItem('finna_csrf');
  if (csrf) config.headers['X-CSRF-Token'] = csrf;
  return config;
});

let refreshPromise: Promise<string> | null = null;

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const original = err.config;
    if (err.response?.status !== 401 || original._retry) throw err;
    if (original.url?.includes('/auth/refresh')) throw err; // avoid loop

    original._retry = true;
    if (!refreshPromise) {
      refreshPromise = api
        .post('/auth/refresh')
        .then((res) => {
          const { access_token, csrf_token } = res.data;
          useAuthStore.getState().setAccessToken(access_token);
          if (csrf_token) localStorage.setItem('finna_csrf', csrf_token);
          return access_token as string;
        })
        .catch((e) => {
          useAuthStore.getState().logout();
          window.location.href = '/login?reason=expired';
          throw e;
        })
        .finally(() => { refreshPromise = null; });
    }

    const newToken = await refreshPromise;
    original.headers.Authorization = `Bearer ${newToken}`;
    return api(original);
  },
);
```

## Auth store (`src/features/auth/store.ts`)

```ts
import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  user: User | null;
  setAccessToken: (t: string | null) => void;
  setUser: (u: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: sessionStorage.getItem('finna_at'),
  user: null,
  setAccessToken: (t) => {
    if (t) sessionStorage.setItem('finna_at', t);
    else   sessionStorage.removeItem('finna_at');
    set({ accessToken: t });
  },
  setUser: (u) => set({ user: u }),
  logout: () => {
    sessionStorage.removeItem('finna_at');
    localStorage.removeItem('finna_csrf');
    set({ accessToken: null, user: null });
  },
}));
```

`useMe()` is the canonical hook for the current user — backed by TanStack Query so it stays fresh and survives reload:

```ts
export function useMe() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['auth','me'],
    queryFn: () => api.get('/users/me').then(r => r.data),
    enabled: !!token,
    staleTime: 5 * 60_000,
  });
}
```

## `LoginPage` wiring

Replace the mockup `setTimeout` simulation with real calls. Visual structure (two-column login card, headline + subtitle on left, SSO list + email fallback on right) **stays as-is** — only swap handlers.

```tsx
function LoginPage() {
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const reason = searchParams.get('reason');
  const [showEmail, setShowEmail] = useState(false);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(reason === 'expired' ? 'Session expired. Sign in again.' : null);

  const { data: providers = SSO_PROVIDERS } = useQuery({
    queryKey: ['auth','providers'],
    queryFn: () => api.get('/auth/providers').then(r => r.data),
    staleTime: Infinity,
  });

  const startSso = async (id: string) => {
    setLoadingId(id);
    try {
      const { data } = await api.post(`/auth/sso/${id}/start`);
      sessionStorage.setItem('finna_oauth_state', data.state);
      window.location.href = data.redirect_url;
    } catch (e) {
      setLoadingId(null);
      setErr(extractError(e));
    }
  };

  const submitEmail = async (form: { email: string; password: string }) => {
    setLoadingId('email');
    try {
      const { data } = await api.post('/auth/login', form);
      useAuthStore.getState().setAccessToken(data.access_token);
      if (data.csrf_token) localStorage.setItem('finna_csrf', data.csrf_token);
      nav('/dashboard', { replace: true });
    } catch (e) {
      setLoadingId(null);
      setErr(extractError(e));
    }
  };

  // …render mockup markup, swap onClick={ssoLogin} → onClick={() => startSso(p.id)}…
}
```

### `AuthCallback`

Lives at `/auth/callback`. Exchanges the OAuth code for tokens, then routes to `/dashboard`.

```tsx
function AuthCallback() {
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return; // StrictMode double-mount guard
    ranRef.current = true;

    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const expected = sessionStorage.getItem('finna_oauth_state');
    sessionStorage.removeItem('finna_oauth_state');

    if (!code || !state || state !== expected) {
      nav('/login?reason=invalid_state', { replace: true });
      return;
    }

    api.post('/auth/token/exchange', { code, state })
      .then(({ data }) => {
        useAuthStore.getState().setAccessToken(data.access_token);
        if (data.csrf_token) localStorage.setItem('finna_csrf', data.csrf_token);
        nav('/dashboard', { replace: true });
      })
      .catch((e) => nav(`/login?reason=${encodeURIComponent(extractCode(e))}`, { replace: true }));
  }, []);

  return (
    <div className="login-wrap">
      <div className="login-card" style={{textAlign:'center', padding:'48px'}}>
        <div className="mono" style={{color:'var(--fg-muted)'}}>// completing sign-in…</div>
      </div>
    </div>
  );
}
```

## `ProtectedRoute`

```tsx
function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.accessToken);
  const me = useMe();
  const location = useLocation();

  if (!token) return <Navigate to="/login" state={{ from: location }} replace />;
  if (me.isLoading) return <FullPageSkeleton />;
  if (me.isError) {
    useAuthStore.getState().logout();
    return <Navigate to="/login?reason=session_invalid" replace />;
  }
  return <>{children}</>;
}
```

## Logout

User-menu → Logout in the sidebar (already wired in `shell.jsx`):

```ts
async function logout() {
  try { await api.post('/auth/logout'); } catch {}
  queryClient.clear();
  useAuthStore.getState().logout();
  window.location.href = '/login';
}
```

Always hard-navigate after logout — clears any cached query state lingering in the React tree.

## Tenancy

Multi-tenant: every authed user belongs to one org (`user.org_id`). The backend scopes all responses by the JWT's `org` claim — frontend doesn't pass `org_id`. If a user belongs to multiple orgs, surface an org switcher in the user menu (`PATCH /users/me { active_org_id }` then refetch `['auth','me']` and invalidate everything).

## Errors

`extractError(e)` maps backend Problem+JSON into a string for the form:

```ts
function extractError(e: unknown): string {
  const ax = e as AxiosError<{ detail?: string; title?: string }>;
  if (ax.response?.data?.detail) return ax.response.data.detail;
  if (ax.response?.status === 401) return 'Invalid email or password';
  if (ax.response?.status === 429) return 'Too many attempts. Try again in a minute.';
  return 'Something went wrong. Try again.';
}
```

Surface it in the existing `.login-error` slot — don't add a toast on the login screen (focus stays on the form).

## Done when

- [ ] `/auth/providers` drives the SSO list (fallback to hard-coded if endpoint 404s).
- [ ] Each SSO button redirects to `redirect_url` with `state` round-tripped via `sessionStorage`.
- [ ] `/auth/callback` exchanges code, stores access token in memory, routes to `/dashboard`.
- [ ] Email-password fallback works.
- [ ] 401 anywhere triggers a single refresh attempt; failure routes to `/login?reason=expired`.
- [ ] Hard refresh on a protected page restores session via the refresh cookie + `useMe()`.
- [ ] `Logout` clears tokens, query cache, and hard-navigates to `/login`.
- [ ] StrictMode double-mount of `AuthCallback` doesn't burn the auth code twice.
