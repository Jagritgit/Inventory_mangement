# InventoryMS

Django 5.1 inventory management system (SQLite). Apps: store, accounts, transactions, invoice, bills.

## Run
- Workflow `Start application`: `python manage.py runserver 0.0.0.0:5000`
- Deployment: autoscale, gunicorn `InventoryMS.wsgi:application` on port 5000.

## Test suite
- Run: `python manage.py test`
- 56 tests across 5 apps: models, forms, views, business logic, integration flow, auth.

## Phase 1 audit fixes (2026-04-23)
- `accounts.Customer.__str__` no longer crashes when `last_name` is `None`.
- Dashboard `total_items` aggregate handles empty DB (returns 0, not None).
- `transactions.SaleCreateView` validates stock and quantity before reducing inventory; raises inside the atomic block so failed sales fully roll back.
- `store.ProductCreateView.test_func` no longer raises `TypeError` comparing a POST string to int.

## Not done in this session (out of scope for one shot)
- Phase 2 architecture refactor, Phase 3 UI redesign, Phase 4 SKU/role-based features,
  Phase 5 deeper backend rework, Phase 7 extras (CSV export beyond xlsx, dark mode, REST API, audit log).

## Replit setup notes
- `ALLOWED_HOSTS = ['*']` and `CSRF_TRUSTED_ORIGINS` set for replit domains in `InventoryMS/settings.py`.
- DB: SQLite at `db.sqlite3`. Migrations applied.
