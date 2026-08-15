.PHONY: dev build test deploy hash-password check-config venv api-install site-install

PY ?= python3
VENV_SITE = site/.venv
VENV_API = api/.venv

venv:
	$(PY) -m venv $(VENV_SITE)
	$(PY) -m venv $(VENV_API)

site-install:
	$(VENV_SITE)/bin/pip install -r site/requirements.txt

api-install:
	$(VENV_API)/bin/pip install -r api/requirements.txt

dev:
	@echo "Starting build-watcher (:8080) and API (:8000) ..."
	( $(VENV_SITE)/bin/python site/build.py --watch --serve --port 8080 & \
	  cd api && ../$(VENV_API)/bin/uvicorn app.main:app --reload --port 8000 )

build:
	$(VENV_SITE)/bin/python site/check_config.py
	$(VENV_SITE)/bin/python site/build.py

test:
	$(VENV_SITE)/bin/python -m pytest site/tests -v
	$(VENV_API)/bin/python -m pytest api/tests -v

check-config:
	$(VENV_SITE)/bin/python site/check_config.py

hash-password:
	$(VENV_API)/bin/python -c "import bcrypt, getpass; pw = getpass.getpass('Пароль администратора: '); print(bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())"

deploy:
	@echo "Frontend: push to main, Netlify builds automatically (see deploy/netlify.toml)."
	@echo "Backend: push to main, Render builds automatically (see deploy/render.yaml)."
	@echo "VPS alternative: docker compose -f docker-compose.prod.yml up -d --build"
