web: uvicorn apps.api.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
worker: python -m apps.api.app.core.outbox
