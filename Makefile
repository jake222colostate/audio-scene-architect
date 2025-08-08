dev:
	@echo "Run backend: uvicorn backend.main:app --host 0.0.0.0 --port 8000"
	@echo "Run frontend: npm run dev"

docker-lite:
	docker build -t soundforge:lite .
	docker run --rm -p 8000:8000 soundforge:lite
