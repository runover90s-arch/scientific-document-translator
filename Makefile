.PHONY: dev test

dev:
	PYTHONPATH=backend uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

test:
	cd backend && PYTHONPATH=. pytest -q
