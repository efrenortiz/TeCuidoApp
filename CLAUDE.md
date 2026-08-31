# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Specification

`specification.md` (repo root) holds the conceptual/functional definition of this Web application, written by the user. Consult it for product intent before making architectural decisions.

## Project state

This is a freshly generated Django 6.1 project (`django-admin startproject`). It currently has no apps, no views, no models, and no README — only the project scaffold (`TeCuidoApp/settings.py`, `urls.py`, `wsgi.py`, `asgi.py`) and `manage.py`. There is no `requirements.txt` yet; Django is installed only in the virtualenv described below.

## Environment

- Virtualenv lives outside this repo at `/home/efren/Documentos/TeCuido` (sibling of `TeCuidoApp/`, the repo root). Activate it before running any Django command:
  ```
  source /home/efren/Documentos/TeCuido/bin/activate
  ```
- Python 3.12.3, Django 6.1.

## Common commands

Run from the repo root (where `manage.py` lives):

- Start dev server: `python manage.py runserver`
- Create a new app: `python manage.py startapp <name>` — then add it to `INSTALLED_APPS` in `TeCuidoApp/settings.py`.
- Make/apply migrations: `python manage.py makemigrations` / `python manage.py migrate`
- Create a superuser: `python manage.py createsuperuser`
- Open the Django shell: `python manage.py shell`
- Run tests: `python manage.py test` (no test apps exist yet)

## Architecture

- Project package: `TeCuidoApp/` — settings module is `TeCuidoApp.settings`, root URL conf is `TeCuidoApp.urls` (currently only wires up `/admin/`).
- Database: SQLite at `db.sqlite3` in the repo root (`DATABASES` in `settings.py`).
- Settings notes:
  - `DEBUG = True` and `SECRET_KEY` is the default insecure generated key — both must change before any production deployment.
  - `ALLOWED_HOSTS` is empty.
  - Email is configured via a non-standard `MAILERS` setting using the console backend (`django.core.mail.backends.console.EmailBackend`); note Django's actual setting name is `EMAIL_BACKEND` — `MAILERS` as written has no effect until wired up properly.
- As apps are added, register them in `INSTALLED_APPS` and route them via `include()` in `TeCuidoApp/urls.py`.
