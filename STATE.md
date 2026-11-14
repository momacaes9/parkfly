# Parkfly continuation state

## Recovered 2026-11-14
- Base: `6cf22a2` from momacaes9/parkfly; clean checkout; sibling parkshark cloned.
- Read CONTEXT.md and PROMPT.md; user request takes priority over attached prompt prose.
- Existing P0–P3 pipeline, browser app, 480-run connectome surface and held-out results preserved.
- Recovered missing ASSUMPTIONS.md, DEMO.md and Birmingham validator from uploaded update ZIP.
- Recovered later GoogleMutant integration from web ZIP; deliberately excluded config.js (may contain keys).
- Colab sanity and intact/input-lesioned response surface cells supplied in chat.
- GitHub CLI credential reports invalid; actual push/provider access still to check.
- No Vercel credential configured; asked user for deployment access while work continues.

## Next
1. Correct and run Birmingham validation without leakage; preserve comparable baselines.
2. Verify P0–P2 outputs and model parity; fix map fallback and all demo controls.
3. Commit checkpoints and push to GitHub. Deploy Vercel if access is available.
4. Record browser verification and concrete remaining limitations here.

## Scientific and map checkpoint
- Official NCSU HTTP 200; 214 features and all focus-lot capacities agree with cache.
- Ran `pipeline/ncsu_lots.py` (Overpass timed out; documented approximate destination/entrances).
- Ran `pipeline/simulate_drivers.py` with fixed train/test seeds; reproduced fitted taus and occupancy snapshots.
- Ran `pipeline/evaluate.py`; 25% within-lot Brier 0.1231 vs 0.1787; placement spread 0.127 vs entrance 0.145.
- Corrected looming mapping in Python and JS and regenerated evaluation: fly 1.57 min vs nearest 1.40 at 25%; old tie is superseded.
- Ran corrected real Birmingham validation: 28 retained lots, 51/22 day split, 32.5% MAE gain; no cross-split interpolation and matched hidden-target baselines.
- Fixed looping basemap fallback; added plain local polygon layer and local fonts. Initial browser inspection works at 1366×768 with external tiles unavailable.
- Added Colab notebook with coarse/full input-lesioned surfaces and raw-run checkpoint support.
- Identified reproducible near-full lesion scene; six demo beats use it, explicitly avoiding an unproven full-lot/crash claim.
- Added read-only Vercel NCSU proxy and official-count check; simulator remains labeled simulated.
- GitHub metadata permits writes, but actual integration blob create returned 403. Separate GitHub device authorization requested.
- Vercel CLI logged out; device authorization requested. Neither push nor deploy is claimed complete.

## Final geography / live-location checkpoint
- Geocoded Hunt Library (OSM way/177166351) and Riddick Hall (way/47917781) via Nominatim; cached source IDs. Display all 203 existing/active positive-capacity NCSU polygons from 214 raw features, retaining 478 focus spots in 7 permit sections / 6 facilities.
- Re-ran the full modern `build_ncstate.py`: simulator, fitting, held-out evaluation, search for lesion scene, posterior-based senses export. Removed the obsolete SEED/template build entry point. Updated both standalone Colab notebooks to input lesions and multi-seed rates.
- Final post-geocode fly at 25%: 1.763 min vs nearest 1.599, success 96.2% each. Supersedes earlier 1.40/1.57 values above. README and DEMO regenerated from JSON.
- Final lesion: weekday seed 1, 09:50, E.B. III, 25% sensors: 5 free now / 0 after 15 minutes. Intact DIVERT (GF about 146 Hz), lesioned COMMIT (GF 0). Searched states, not fabricated data.
- Added live browser geolocation per user request: permission button, watch updates, accuracy circle, stop/clear, denial/timeout handling, campus refocus. GPS changes estimated trip cost into the real connectome surface. No coordinate upload/storage. Basemap providers receive viewed-area tile requests.
- Browser tests used mocked positions, including update and denial. Actual user-device location permission must be granted by the user and was not accessed here.
- Exported real group-level network from downloaded Connectivity_783.parquet; network graphic and lesion edge are driven by those counts.
- First temporary Vercel deployment was claimed by user, so anonymous updates now fail by design. Existing claimed site updates require Vercel login. Fresh CLI device authorization requested. Latest final preview uses a second anonymous deployment; keep URL/claim instructions in final chat.
- GitHub OAuth login returned a token with no scopes; authenticated Git push and GitHub Git-blob POST still return 403. No remote push is claimed. Preserve local commits in a Git bundle for recovery.

## Final verification and access status
- Python: 3 tests pass. Node parity/placement: 2 tests pass. Full scripted browser suite covers all tabs, controls, destination switch, six-beat demo, network projection lesion, and offline map fallback; no page or console errors.
- Browser geolocation tests use deterministic mock fixes and confirm update, denial, stop/clear, and absence of explicit coordinate uploads. Native initial geolocation was also exercised with a browser emulated fix; the user's actual GPS has not been accessed.
- Read-only NCSU serverless API verified live: HTTP 200, 214 official features.
- Vercel account authorization is blocked at the user's authenticator 2FA prompt; only the user's authenticator or recovery code can complete it. No 2FA code can be generated here.
- Current final preview: https://sonic-harp-nf3wun7.tmp.now (temporary until owner claims it). Earlier claimed fleet-gust deployment remains in owner's account but cannot be updated without CLI authorization.
- Final hosted browser verification passed on https://sonic-harp-nf3wun7.tmp.now: no page errors, no console errors, no HTTP failures; slider updates 10–21 ms in that run. Official hosted API returns 214 features. All final controls, network lesion and six demo beats exercised.
- Final GitHub reattempt: both `git push origin main` and connected-app contents API returned 403. Repository metadata permissions do not correspond to a usable contents-write credential in this session. No remote commit was created.

## Visible live API / neuron connection (user follow-up)
- Use my location now opens the fly tab and starts an official NCSU API check automatically.
- Added a connection card reporting device GPS/permission state, official API verification vs cached map, and the real 138,639-neuron measured response table.
- Device fixes open the real network diagram and update per-lot estimated drive costs and neural readouts. Stop clears GPS; queued callbacks after stopping are ignored.
- No live parking occupancy is invented. GPS is actual device input only after browser permission; drive time is estimated and connectome output is table interpolation.
- GitHub permission refresh accepted by user again, but token still reports no scopes and write returned 403. Repeated logins do not fix the repository write permission.
- Verified the hosted `?connect=1` path: fly panel opens immediately; mocked GPS updates feed neural outputs, the NCSU API automatically verifies 214 official polygons, Stop clears location, and denied permission preserves the app. No page errors. Actual physical user GPS remains dependent on the user's browser permission.

## Vercel account setup and real production deployment (supersedes temporary-hosting blockers above)
- User's latest CLI device authorization succeeded: authenticated as momacaes9.
- Followed https://vercel.com/get-started.md. Installed CLI 65.16.0 globally; bare `vercel whoami` works.
- Official plugin installation for Codex failed because neither curated marketplace contains it. Checked plugin docs and installed the documented fallback: 9 global official agent skills for Codex.
- Shared global MCP registered at https://mcp.vercel.com in /home/agent/.codex/config.toml. OAuth is still incomplete; user reported the authorization URL did not work. No MCP list_teams success is claimed.
- Linked existing monica-a634/parkfly and deployed production, dpl_HXaD51Kn5T1viWem6363NajKJPPW.
- Permanent project URL: https://parkfly-one.vercel.app . Public page and NCSU API return HTTP 200; API has 214 official features.
- Production browser verification passed all controls/demo/lesion/offline checks without page, console or HTTP errors; geolocation grant/update/deny/stop tests passed with mock device fixes.
- Global credentials and local OIDC files remain outside Git. GitHub write access is a separate outstanding blocker.

## Owner updates, dashboard cleanup, branding and calibrated encoder
- Fetched owner commit 1015600 adding the production link to README. Both origin/main and origin/V5 pointed to it. Merged it into the work branch while retaining the same production URL and full documentation.
- Work branch: codex/parkfly-dashboard-accuracy. Prior production code remained available during changes.
- Built training-only fly encoder calibration on 14 simulated weekdays, 81 candidate settings; evaluated on four different days with identical policy masks. 25% coverage: calibrated 96.79% (151/156), original 96.15% (150/156); 1.583 vs 1.763 min. Small paired gain interval includes zero. Original benchmark curve was reproduced exactly.
- Added Python/JS parity checks for calibrated inputs and neuron outputs; vectorized measured-surface interpolation is checked against the original scalar implementation. Five Python tests and Node parity tests pass.
- Cleaned map labels, collapsed map key and source/connection detail, moved direct actions to a small map toolbar, made unsensed accuracy the primary KPI, and added measured fly success/cost and 95% day-bootstrap evidence with methodology details.
- Latest user direction applied: 🪰 ParkFly branding only in the app, with simulation focus. Read all four pages of the uploaded NC State starter PDF. Main numerical libraries already match its simulator; optional skeleton libraries are documented separately and available in an off-by-default Colab cell. No FlyWire token used or saved in source.
- Rewrote README around the real connectome, fixed LIF model, encoder training algorithm, precise sample counts/metrics, uncertainty, libraries and reproducibility. No Arduino mention or commercial hardware pitch.
- Diagnosed fresh production 404: GitHub auto-deploy from root generated a ready deployment without the app index. Promoted the known-good deployment and verified HTTP 200. Changed project root to web and linked repository root for subsequent CLI builds, so Git deployment uses the actual app directory.

## Presentation handoff
- Read the newly pasted starter source. Prepared presentation/DEMO_LIVE.md (680 spoken words, six app demo beats, four-/five-minute cuts), DEMO_VIDEO.md, DEMO_QA.md (26 questions + exact number card), PRESENTATION.md (five backup slide outlines, no generated images).
- Published-guide assets prepared under web/lab, including a readable demo.html with live/video/Q&A/presentation tabs and print/download controls. All metrics are copied from current result exports; optional skeleton/flybody scope is explicitly disclosed.
- Follow-up production test exposed a test transport issue: Playwright APIRequest used a direct network path and failed downloading the notebook, while browser app/location flows worked. Changed that asset check to browser fetch, matching actual user access.

## Verified collaborator handoff and canonical production
- Canonical production is Ready: dpl_6WjkJUAVqkXhD1xyJokdPZZjYqH6, https://parkfly-one.vercel.app. The published bundle metadata matches local SHA-256 ecc37b5a1bf7caafd52f237d05d5425c3a927c035c36f1d26a8cc8ad17246c51.
- Published bundle imports branch codex/parkfly-lab at 5b2ea02, including the application, experiments, README, presentation and source ZIP. GITHUB_HANDOFF.md provides three commands for an already-authorized collaborator to push that branch.
- Final production browser and mocked-GPS reports pass, with no page/console/HTTP errors. Verification screenshots and reports are committed with this checkpoint.
- Latest remote heads remain main/V5 at 1015600 and KungFuArtist-patch-1 at ca869f7; Ishan's new branch name is pending. Latest dry-run push still returns HTTP 403. No GitHub publication is claimed.
- Invitations shown for codex and Chatgpt-openai-helper do not grant this session access: it does not control those public accounts.

## Ishan V6
- Fetched origin/V6 at 47dab17 and merged all source history locally without conflicts. Preserved his source and published /v6/ in the existing web root. Main lab links to it; V6 links back.
- Changed V6 display branding to ParkFly and labeled imported neural outputs, heuristic fallback, occupancy/layout estimates. Corrected the hour mismatch that previously retained recorded 10am neural decisions at other hours. Removed committed Python bytecode.
- Python tests: five pass. Node parity/placement: two pass. Git dry-run push still returns 403; local integration is not a remote merge.

## Final README and V6 publication
- Published /v6/ at the canonical project; production V6 browser test passed search/reset, weekday/Saturday, time controls, lot detail and three fly animations with no page errors.
- README ends with an explanatory results table, exact V6 embedded counts (144 lots, 17,527 capacity spaces, 75 modeled layouts, 9 destinations, 14 recorded decisions, 3 recorded journeys), library roles and live-data limitations. Proposed repository description is saved in GITHUB_DESCRIPTION.md; metadata PATCH also returned 403.
- To avoid recursively bundling old binary recovery packages, the refreshed collaborator branch consolidates the current source tree onto origin/V6 and omits the bundle itself and its metadata. Local full development history remains on main.
