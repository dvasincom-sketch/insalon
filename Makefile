dev:
	source venv/bin/activate && uvicorn app.main:app --reload

push:
	git add . && git commit -m "update" && git push origin main

sync:
	open http://localhost:8000/sync/all

analytics:
	open http://localhost:8000/analytics/summary