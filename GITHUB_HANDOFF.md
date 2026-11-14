# ParkFly integration handoff for the repo owner / Ishan

## What is ready

- Canonical production: https://parkfly-one.vercel.app
- Vercel project: monica-a634/parkfly. Git repository: momacaes9/parkfly. Production branch: main. Root directory: web.
- Latest implementation: combined validated lab + upstream V6 at 47dab17 + final README results table.
- Bundle revision and SHA-256: see https://parkfly-one.vercel.app/lab/bundle-version.json.
- Bundle branch: codex/parkfly-lab. This is a new review branch; importing it does not overwrite your working branch or main.
- The owner README commit 1015600 is already merged into this checkpoint.

## Upload the actual commits using your existing GitHub write access

Run inside your existing clone of momacaes9/parkfly. These commands create/import a separate branch and push only that branch:

```sh
curl -fL https://parkfly-one.vercel.app/lab/parkfly-changes.bundle -o /tmp/parkfly-changes.bundle
git fetch /tmp/parkfly-changes.bundle refs/heads/codex/parkfly-lab:refs/heads/codex/parkfly-lab
git push -u origin codex/parkfly-lab
```

The bundle retains upstream V6 history and consolidates the lab integration into one review commit. Local development checkpoints remain preserved separately. No patch or manual file copying is required. Its branch includes the actual application code, trained-encoder experiment, numerical tests, current README, and presentation materials. It contains no runtime credential files.

Then compare `codex/parkfly-lab` against `main` in GitHub and open a pull request. The Ishan V6 branch at 47dab17 is already merged into this bundle. Both the lab and /v6/ publish from web in one project. Avoid force-pushing a shared branch.

## Unify the Vercel deployments

Keep monica-a634/parkfly and https://parkfly-one.vercel.app as the single canonical production target. Merge reviewed changes into main. Branches can use preview deployments within that project. Confirm the root stays web. Deploy the merged app from the repository root with:

```sh
vercel deploy --prod --yes --scope monica-a634
```

The previously restored production is already public. Do not connect another project to the same production alias or change the app root back to the repository root; that previously caused a 404. Older temporary deployments can remain separate during review; they are not the canonical link.

## Why an invitation to a GitHub username did not unblock this session

This session is authenticated through a connection for momacaes9. It does not control the public accounts named codex or Chatgpt-openai-helper and cannot accept invitations addressed to those accounts. GitHub writes from the session have returned HTTP 403 even while repository reads work. The workflow above lets an existing authorized collaborator publish the prepared commits without sharing credentials in chat.
