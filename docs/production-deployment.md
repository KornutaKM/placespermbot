# Production deployment: operator-run checklist

This repository does **not** have production server credentials, an automated
SSH deploy, or an active release pipeline. All commands below must be run
manually on the actual authorized host by an operator with the correct bot
token and Docker Compose access. This guide does not imply a bot has been
deployed or restarted.

## Principles and prerequisites

- Record the approved new Git SHA and previous running SHA before any change.
- Verify the checkout matches the reviewed commit; CI success is not a deployed version.
- Preserve the Compose named volume `places-data`. Never run
  `docker compose down -v`, `docker volume rm`, or delete SQLite WAL files.
- Confirm `.env` is not committed, contains the actual bot token, and has
  `PLACES_ENVIRONMENT=production` and
  `PLACES_DATABASE_PATH=data/places.db`.
- Confirm the service has a single polling instance: a second instance with
  the same Telegram token can conflict with the running bot.
- Have a private **host backup directory outside the Docker volume** and
  enough free disk space. Do not upload user databases to GitHub Actions.

## Step 1 — validate the current service and create an online backup

On the authorized host, from the repository directory:

```bash
docker compose config --quiet
mkdir -p backups
chmod 700 backups
docker compose ps
docker compose exec -T bot python -m app.healthcheck

SNAPSHOT="places-$(date -u +%Y%m%dT%H%M%SZ).db"
docker compose run --rm --no-deps -v "$PWD/backups:/backups" bot \
  python -m app.database_backup /app/data/places.db "/backups/$SNAPSHOT"
chmod 600 "backups/$SNAPSHOT"
```

The backup command uses SQLite Backup API on the live WAL database and
validates the output before publishing the file. Keep the backup host-side,
**outside** the named volume. Never copy only `places.db` while the bot
is live: that can omit uncheckpointed WAL content.

## Step 2 — prepare and review the candidate image without starting polling

Check out the approved Git SHA (use your normal reviewed release procedure).
Then run:

```bash
APPROVED_SHA="$(git rev-parse HEAD)"
docker compose build --build-arg "PLACES_BUILD_SHA=$APPROVED_SHA" bot
docker compose run --rm --no-deps \
  -v "$PWD/backups:/backups:ro" bot \
  python -m app.deployment_preflight --backup "/backups/$SNAPSHOT" \
  --expected-sha "$APPROVED_SHA" --max-age-hours 24 --min-cities 33
```

The preflight also rejects hard links or aliases pointing at the live SQLite
file: a filesystem link is not a WAL-consistent backup.

The Docker image embeds the Git SHA as the OCI image label and the
`PLACES_BUILD_SHA` environment variable. Preflight rejects a missing,
malformed or mismatching SHA even if the backup and SQLite checks pass.
**Do not set PLACES_BUILD_SHA in the server .env file or override it in Compose:**
the value must come from the approved Docker image. In the Docker build
command above, APPROVED_SHA must refer to the reviewed *full* Git commit.
The preflight opens the live DB and backup **read-only**, checks the full
database contract, source catalog validation, backup freshness and count of
registered cities, and returns a small JSON status without secrets, user
records or file paths. It **does not** restart containers, run migrations or
prove Telegram network connectivity. The live SQLite schema must already
match the code version's known migration contract; if you plan a schema
migration, use a separately reviewed migration procedure rather than
bypassing failed preflight.

A failed or stale preflight must stop the release. Do not adjust database
timestamps to make an old backup look fresh.

## Step 3 — start the candidate and validate it

Only after explicit operator approval and successful preflight:

```bash
docker compose up -d --no-deps --no-build bot
docker compose ps
docker compose exec -T bot python -m app.healthcheck
docker compose exec -T bot python -m app.diagnostics
# Confirm the "build_sha" field in the diagnostics JSON equals $APPROVED_SHA.
docker compose logs --tail=100 bot
```

Check Telegram `/start`, city selection and a saved route with a test account.
Any schema migrations are executed by `app.main` at startup. Keep the
timestamped backup until post-release validation and retention policy allow
its secure deletion.

## Failure and rollback

1. Stop the bot and retain logs and the snapshot. Avoid duplicate polling.
2. A code-only rollback is **not** automatically safe if the DB schema has
   advanced. First compare the old code's supported migration versions.
3. If database restoration is explicitly authorized, understand that writes
   since the snapshot will be lost. Stop all bot instances, inspect the snapshot,
   and use `python -m app.database_restore` from a compatible image with the
   named volume and a **read-only host backup mount**.
4. Validate restored DB contract and health before resuming Telegram polling.
   Never restore into a live DB or edit `-wal`/`-shm` files by hand.

There is deliberately no unattended production deployment workflow. CI
success and a GitHub merge do not establish that a server was updated.
