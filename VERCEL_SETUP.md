# Vercel setup and deployment

Source playbook: https://vercel.com/get-started.md, followed on 2026-11-14.

## Verified
- Vercel CLI 65.16.0 installed globally for this user at `/home/agent/.local/bin/vercel`.
- Bare `vercel whoami` authenticates as `momacaes9`; credentials remain outside Git in user-scoped storage with restrictive file permissions.
- Preferred plugin installation was attempted for Codex. Both curated catalogs rejected it as not found. The plugin documentation was checked before falling back.
- Installed the official `vercel-labs/agent-skills` package globally for Codex: 9 skills under `/home/agent/.agents/skills`. Confirmed by `npx skills list --global`. No duplicate plugin installation is active.
- Added shared global MCP entry `vercel` with URL exactly `https://mcp.vercel.com` to `/home/agent/.codex/config.toml`, preserving other settings. Human confirmation settings were not disabled.
- Existing project `monica-a634/parkfly` linked only after global CLI setup, for the user-authorized deployment operation. The Vercel project root setting is `web`; invoke the CLI from the repository root.
- Production URL: https://parkfly-one.vercel.app
- Production deployment: `dpl_HXaD51Kn5T1viWem6363NajKJPPW`.
- Public production page and `/api/ncsu` returned HTTP 200; official API returned 214 features.
- Full production browser verification passed, including all map controls, six-beat demo and lesion scene, and offline fallback; no page/console/HTTP errors. Device-position tests use mock coordinates, not the user's physical GPS.

## Still pending
- MCP OAuth has not completed. Codex lists the server as enabled, not logged in. The user reported that the browser authorization link did not work; verbal consent does not complete the OAuth callback. The client metadata URL itself was checked and returned HTTP 200. No authenticated MCP `list_teams` call is claimed.
- The MCP configuration is registered and visible without restarting. Authenticated tool checks must run after completing OAuth.
- GitHub push is independent of Vercel authentication and has returned HTTP 403. Local history and a verified recovery bundle preserve the implementation; no remote GitHub merge is claimed.

## Operations

```sh
vercel whoami
vercel deploy --prod --yes --scope monica-a634
```

No CLI credential, OIDC token, `.env.local`, or `.vercel` metadata is tracked in Git. No new account was created and no unrelated project was changed.

## Root-directory correction
An owner README commit triggered an automatic Git build from repository root and replaced the working production alias with a 404 deployment. Restored the previous deployment and set project root to `web` with `vercel project update parkfly --root-directory web`. Repository-root CLI linking now matches that setting.
