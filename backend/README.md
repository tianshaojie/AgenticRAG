# Backend Scaffold

## Quick Start

1. Copy `.env.example` to `.env` and adjust values.
2. Create virtualenv and install deps:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -e .[dev]`
3. Run API:
   - `uvicorn app.main:app --reload`
4. Run migrations:
   - `alembic upgrade head`
5. Run tests:
   - `pytest -q`

## Notes

- This phase contains only architecture and interface skeletons.
- Retrieval, reranking, and answer generation are intentionally stubbed.
