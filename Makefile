PY := .venv/bin/python
.PHONY: install demo fixture doctor test lint typecheck build benchmark resume-metrics serve
install:
	uv sync --frozen
	npm ci --prefix frontend
demo:
	$(PY) -m scripts.dev
fixture:
	$(PY) -m scripts.dev --fixture
doctor:
	$(PY) -m scripts.doctor
test:
	$(PY) -m pytest
	npm test --prefix frontend
lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	npm run lint --prefix frontend
typecheck:
	.venv/bin/mypy
	npm run typecheck --prefix frontend
build:
	npm run build --prefix frontend
benchmark:
	$(PY) -m benchmarks.run --dataset benchmarks/data/synthetic.jsonl --pipeline baseline_llm
	$(PY) -m benchmarks.run --dataset benchmarks/data/synthetic.jsonl --pipeline two_stage
resume-metrics:
	$(PY) -m benchmarks.compare --resume

serve: build
	$(PY) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
