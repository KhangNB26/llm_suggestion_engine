from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.test_runner import run_test

# List of all test cases
ALL_TCS = ["tc01", "tc02", "tc03", "tc04", "tc05",
           "tc06", "tc07", "tc08", "tc09", "tc10"]

app = FastAPI(title="AI Plan Test API",
              description="Expose LLM test runner as HTTP endpoints",
              version="1.0.0")

class RunTestRequest(BaseModel):
    tc: str

@app.post("/run_test")
def run_test_endpoint(req: RunTestRequest):
    if req.tc not in ALL_TCS:
        raise HTTPException(status_code=400,
                            detail=f"Unknown test case {req.tc}. Valid: {ALL_TCS}")
    try:
        result = run_test(req.tc)
        return {"tc": req.tc, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run_all")
def run_all_endpoint():
    results = {}
    for tc in ALL_TCS:
        try:
            results[tc] = run_test(tc)
        except Exception as e:
            results[tc] = {"error": str(e)}
    return results
