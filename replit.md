# InventoryMS

Django 5.1 inventory management system (SQLite). Apps: store, accounts, transactions, invoice, bills.

## Run
- Workflow `Start application`: `python manage.py runserver 0.0.0.0:5000`
- Deployment: autoscale, gunicorn `InventoryMS.wsgi:application` on port 5000.

## Replit setup notes
- `ALLOWED_HOSTS = ['*']` and `CSRF_TRUSTED_ORIGINS` set for replit domains in `InventoryMS/settings.py`.
- DB: SQLite at `db.sqlite3`. Migrations applied.
