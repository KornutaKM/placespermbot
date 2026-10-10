# Windows Docker: occasional local release updates

This procedure is **operator-initiated**, not an unattended deploy. It targets
the development bot on Windows Docker Desktop; there is no connection from
GitHub Actions to the operator's workstation. Merging a pull request does not
restart the running Telegram bot.

## Requirements

- An existing healthy `bot` service under Docker Compose, with a
  working `.env` containing `PLACES_ENVIRONMENT=development`.
- Git, Docker Desktop with Compose, and PowerShell.
- No other Telegram polling instance using the same token.
- A clean working tree (the ignored local `.env` stays unchanged).
- A reviewed and CI-green **full 40-character commit SHA** from `main`.
  The script checks that this commit is an ancestor of `origin/main`.

The script deliberately refuses production and an uninitialized/stopped bot.
For production, use [production-deployment.md](production-deployment.md).

## One command, when you choose to update

From the repository on your Windows machine:

```powershell
.\scripts\update-local.ps1 -ApprovedSha "<reviewed-40-character-main-sha>"
```

If Windows PowerShell's execution policy blocks local scripts, prefer an
approved local policy or run the script in PowerShell 7 according to your
machine's security rules. Avoid disabling security policies globally.

The default host-side backup directory is a sibling of the repository:
`D:\projects\placespermbot-backups` for checkout `D:\projects\placespermbot`.
To set a different private backup location:

```powershell
.\scripts\update-local.ps1 -ApprovedSha "<reviewed-40-character-main-sha>" `
  -BackupDirectory "D:\private\places-backups"
```

## Safety sequence

1. Fetch `origin/main`, verify a clean worktree, approved commit, Compose
   configuration, running bot, development environment, and health.
2. Use SQLite Online Backup API from the **currently running image** to
   create and verify a timestamped snapshot outside the named volume.
3. Switch the source checkout to the approved SHA and build a pinned image.
4. Run the candidate image with the **read-only local release preflight**
   against the live database and snapshot: validate expected Git SHA,
   freshness, independence, schema, SQLite integrity and catalog count.
   This container does **not** start Telegram polling.
5. Replace only the Compose `bot` service, then verify health and the
   reported `build_sha` from diagnostics.

Failures before step 5 leave the previous polling container running; no
automatic database restoration takes place. Failures after replacement
require examining logs, schema compatibility and the retained snapshot
before an explicitly authorized recovery. Do not assume a code-only rollback
is safe if a newer version performed migrations.

The script never deletes `places-data`, runs `docker compose down -v`,
manually copies a live WAL file, or prints bot credentials. Keep backups
private and apply a deliberate retention policy. The script does not confirm
user-facing Telegram behavior; test `/start`, `/city` and a saved route
after updating.

**Batching updates is fine.** You can leave the working local container on
an older checked SHA while development proceeds through multiple reviewed
commits, and run this command only when you want the consolidated changes.
There is no scheduled or automatic polling/deployment agent included.
