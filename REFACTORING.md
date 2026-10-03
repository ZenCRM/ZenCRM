# Structural refactoring and rollback

Branch: `refactor/structure`.
Baseline: release `0.9.0.4`, commit `1e1de8d36ea638a595462064341ee4d21fb5e587`.

This branch changes code organization. It does not introduce a database migration,
change the release version, or publish a new production Docker image.

## Structure

- `app/__init__.py` retains the application factory and initialization order.
- `app/bootstrap/routes.py` registers the existing blueprints and permission hook.
  Preserve blueprint names, endpoint names, route methods and registration order:
  authentication and authorization use endpoint identities.
- `app/bootstrap/frontend.py` registers page routes and portal address dispatch.
- `app/bootstrap/database.py` contains the existing startup schema compatibility
  code verbatim. It is not a new migration system. Its existing exception handling,
  SQLite-specific operations and SMS compatibility statements remain unchanged.
- `app/services/document_service.py`, `offer_service.py` and `ticket_service.py`
  contain extracted domain helpers. HTTP handlers retain authorization, response
  serialization, and commit/rollback boundaries. Compatibility imports preserve
  the previous helper names. Portal ticket assignment uses the service directly.
- `app/utils/http_responses.py` owns the existing rendered-document CSP response.
- `frontend/js/core/` contains authentication/profile, navigation and startup methods.
- `frontend/js/settings/` contains settings sections. `modules/settings.js` composes
  them at the original position in the feature registry.

Frontend precedence remains **core component → UX → feature modules**. Copy property
descriptors, not evaluated property values, to preserve getters. Create mutable state
inside each factory, and declare script order in `frontend/views/head.html`. Bump the
script query version when changing a module's loading dependencies.

SMS API, model, view and frontend module files have not been refactored. Push worker
scheduling, retry behavior, database upgrade behavior and public API responses are
outside this structural change. Any future behavior change should be reviewed separately.

## Verification

```sh
python -m unittest discover -s tests -v
node --test tests/test_*.cjs
python tools/audit_i18n.py
git diff --check
```

`tests/fixtures/app_contract.json` was captured before extraction from the released
Docker image. It records routes/methods, security hook order, access mappings and the
SQLite schema. `frontend_contract.json` records initial component state, descriptors
and method/getter hashes from the original code in production script order. Fixed
time makes the frontend comparison deterministic. These snapshots deliberately
reject behavioral changes; do not regenerate them just to silence a refactoring failure.
An intentional feature change needs a reviewed fixture update and behavioral tests.

The existing regression suites remain enabled, including SMS isolation, public
helpdesk, JWT invalidation, portal access and PDF/HTML security tests. New integration
checks also verify repeatable factory registration and serving every component script.

## Rollback

Before merge, the stable release remains on `main`. With a clean tracked working tree,
return to it with:

```sh
git switch main
```

Keep the refactor branch for comparison or later work. No production database change
or application downgrade is needed just to switch branches.

The work is split into commits: contract tests (`ae7c373`), backend bootstrap
(`00580b7`), frontend composition (`560dc86`), and domain helpers (`17b8a4e`), followed
by verification/documentation. Revert later dependent commits before earlier ones.
For a complete rollback after integration, revert the refactoring PR as a whole on
a new branch and run CI. Use `git revert`, not a forced reset of shared history.

For an isolated runtime trial, use a separate container, port and disposable test
data. Do not point an experimental container at production volumes. If this branch
is later deployed, retain the prior image digest and a tested data backup. The known
baseline image is:

```text
kosiorekmateusz/zencrm@sha256:005c64b73bf1af0060da85e7149b2a65c1dbcfbce8b92225023086d579aec72e
```

Switching containers back to that image restores the baseline application code.
Do not restore a database backup merely to roll back this refactor: that would discard
new records, and this branch has no schema changes.
