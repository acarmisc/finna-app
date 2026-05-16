# OIDC Setup Guide

Finna supports OpenID Connect (OIDC) for enterprise single sign-on (SSO). This guide walks through configuring common identity providers.

## Keycloak (Recommended for Testing)

Keycloak is open-source and ideal for local testing and development.

### 1. Start Keycloak

```bash
docker run -d -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  keycloak/keycloak:latest start-dev
```

Access at `http://localhost:8080`. Log in with `admin/admin`.

### 2. Create Realm

1. Hover over "Master" (top-left dropdown)
2. Click "Create Realm"
3. Name: `finna`
4. Click "Create"

### 3. Create Client

1. Left menu → Clients
2. Click "Create client"
3. Client ID: `finna-app`
4. Client type: OpenID Connect
5. Click "Next"
6. Toggle "Standard flow enabled" (already on)
7. Click "Save"

### 4. Configure Client

In the client settings page:

- **Access Type:** confidential (set via "Capability config" if needed)
- **Valid Redirect URIs:** Add your callback URL:
  - Local: `http://localhost:5173/auth/oidc/callback`
  - Production: `https://your-domain.com/auth/oidc/callback`
- Click "Save"

### 5. Get Client Secret

1. Click "Credentials" tab
2. Copy the "Client secret" value

### 6. Create Roles & Groups (Optional but Recommended)

#### Create Admin Role

1. Left menu → Roles
2. Click "Create role"
3. Role name: `finna-admins`
4. Click "Create"

#### Create Group

1. Left menu → Groups
2. Click "Create group"
3. Name: `finna-admins`
4. Click "Create"
5. Click "Role mapping"
6. Under "Realm roles", assign `finna-admins` role
7. Click "Assign"

#### Create Test User

1. Left menu → Users
2. Click "Add user"
3. Username: `testadmin`
4. Email: `testadmin@example.com`
5. Click "Create"
6. Click "Credentials", set password (toggle "Temporary" off)
7. Click "Groups", add to `finna-admins` group

### 7. Configure Claim Mapper

1. Go back to "finna-app" client
2. Click "Mappers"
3. Click "Create mapper"
4. Name: `groups`
5. Mapper type: "Group Membership"
6. Token claim name: `groups`
7. Full group path: OFF
8. Add to ID token: ON
9. Click "Save"

### 8. Add to Finna Settings

In Finna admin UI (Settings → Authentication):

- **Name:** Keycloak
- **Issuer:** `http://localhost:8080/realms/finna`
- **Client ID:** `finna-app`
- **Client Secret:** (from step 5)
- **Scopes:** `openid profile email`
- **Claim Mappings:**
  - Username: `preferred_username`
  - Email: `email`
  - Is Admin: `groups` (match: `finna-admins`)
- Click "Test" → should see discovery + JWKS success
- Click "Add Provider"

## Okta

### 1. Create App Integration

1. Okta Admin Dashboard
2. Applications → Applications
3. "Create App Integration"
4. Sign-in method: "OIDC - OpenID Connect"
5. Application type: "Web"
6. Click "Next"

### 2. General Settings

- App integration name: `Finna`
- Grant type: "Authorization Code"
- Sign-in redirect URIs:
  - Local: `http://localhost:5173/auth/oidc/callback`
  - Production: `https://your-domain.com/auth/oidc/callback`
- Controlled access: "Skip group assignment for now"
- Click "Save"

### 3. Copy Credentials

From the app page:
- Copy **Client ID** and **Client Secret** (click "Show" in Client Credentials section)
- Note the **Okta domain** (e.g., `dev-12345.okta.com`)

### 4. Configure Claims (Optional)

1. Go to Security → API → Authorization Servers
2. Click "default"
3. Claims tab
4. Add claim:
   - Name: `groups`
   - Value type: Groups
   - Filter: `.*`
   - Include in: ID Token, Access Token

### 5. Assign Users

1. Back to app page
2. "Assignments" tab
3. Click "Assign" → "Assign to Users"
4. Add test user, set group membership

### 6. Add to Finna Settings

In Finna admin UI:

- **Name:** Okta
- **Issuer:** `https://dev-12345.okta.com`
- **Client ID:** (from step 3)
- **Client Secret:** (from step 3)
- **Scopes:** `openid profile email`
- **Claim Mappings:**
  - Username: `preferred_username`
  - Email: `email`
  - Is Admin: `groups` (match your admin group name)
- Click "Test" and "Add Provider"

## Azure AD

### 1. Register Application

1. Azure Portal → Azure Active Directory
2. App registrations → "New registration"
3. Name: `Finna`
4. Supported account types: "Accounts in this organizational directory only"
5. Redirect URI:
   - Type: Web
   - URI: `http://localhost:5173/auth/oidc/callback` (or prod URL)
6. Click "Register"

### 2. Create Client Secret

1. Certificates & secrets
2. "New client secret"
3. Description: `Finna API`
4. Expires: 12 months (or custom)
5. Click "Add"
6. Copy the **Value** (secret — only shown once)

### 3. Expose an API (Optional)

1. Expose an API
2. "Add a scope"
3. Scope name: `api://Finna`
4. Click "Save and continue"

### 4. Add Users to App

1. Enterprise applications → Finna
2. Users and groups → "Add user/group"
3. Select users/groups to grant access

### 5. Configure Token Claims (Optional)

1. Token configuration
2. "Add optional claim"
3. Token type: ID
4. Add: `groups` (Groups assigned to user)
5. Click "Add"

### 6. Get Tenant Info

On the app overview page, copy:
- **Application (client) ID**
- **Directory (tenant) ID**
- **Issuer URL:** `https://login.microsoftonline.com/{tenant-id}/v2.0`

### 7. Add to Finna Settings

In Finna admin UI:

- **Name:** Azure AD
- **Issuer:** `https://login.microsoftonline.com/{tenant-id}/v2.0`
- **Client ID:** (Application ID from step 6)
- **Client Secret:** (from step 2)
- **Scopes:** `openid profile email`
- **Claim Mappings:**
  - Username: `preferred_username`
  - Email: `email`
  - Is Admin: `groups` (match Azure group name or object ID)
- Click "Test" and "Add Provider"

## Google (OAuth2)

### 1. Google Cloud Console

1. Create a new project or select existing
2. APIs & Services → Credentials
3. "Create Credentials" → "OAuth client ID"
4. Application type: "Web application"
5. Authorized redirect URIs:
   - Local: `http://localhost:5173/auth/oidc/callback`
   - Production: `https://your-domain.com/auth/oidc/callback`
6. Copy **Client ID** and **Client Secret**

### 2. Add to Finna Settings

Google uses standard OAuth2, so in Finna admin UI:

- **Name:** Google
- **Issuer:** `https://accounts.google.com`
- **Client ID:** (from step 1)
- **Client Secret:** (from step 1)
- **Scopes:** `openid profile email`
- **Claim Mappings:**
  - Username: `email` (Google uses email as sub)
  - Email: `email`
  - Is Admin: (optional, not available from Google)
- Click "Test" and "Add Provider"

## Testing

After adding a provider in Finna Settings:

1. Click "Test" button — should show green checkmarks for:
   - Discovery endpoint accessible
   - JWKS endpoint reachable
   - Configuration valid

2. Log out and test sign-in:
   - On login page, click provider button
   - Authenticate at IdP
   - Should redirect back to Finna and set session

3. If sign-in fails, check:
   - Redirect URI matches exactly (including http/https, trailing slashes)
   - Client ID/Secret are correct
   - IdP issuer URL is accessible
   - User has required groups/roles for admin claim mapping

## Troubleshooting

**"Invalid state" error:**
- Clear browser cookies and try again
- Ensure only one Finna tab is open
- State tokens expire after 10 minutes

**"JWKS fetch failed":**
- Verify issuer URL ends with `/` or `/realms/{realm}` (depends on IdP)
- Check firewall/proxy allows HTTPS to IdP

**"User not found after login":**
- Check user exists in IdP
- Verify email claim is present in ID token
- Check claim mappings in provider config

**Groups/admin claim not working:**
- Verify user is assigned to group/role in IdP
- Check group name matches exactly (case-sensitive)
- Use "Test" button to see actual token claims

## Security Notes

- **Secrets:** Never commit `Client Secret` to git. Store in `.env`, GKE secrets, or GitHub environment variables.
- **PKCE:** Finna always uses PKCE S256 for authorization flow (protects against token interception).
- **State token:** Expires after 10 minutes and is single-use (prevents CSRF).
- **Email collision:** If a user already exists in Finna with the same email from a different provider, manual merge is required (prevents account takeover).
