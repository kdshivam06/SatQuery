import httpx, json

r = httpx.get("http://localhost:8000/api/runs?limit=3")
runs = r.json().get("runs", [])

for run in runs:
    rid = run["run_id"]
    status = run["status"]
    error = run.get("error", "none")
    print(f"\n{'='*60}")
    print(f"Run: {rid}")
    print(f"Status: {status}")
    print(f"Error: {error}")
    print(f"Query: {run.get('query','')}")
    print(f"Answer: {str(run.get('answer',''))[:200]}")
    print(f"Current step: {run.get('current_step','')}")
