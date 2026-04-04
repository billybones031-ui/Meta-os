from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Meta-OS")

DESTRUCTIVE_KEYWORDS = {"delete", "erase", "remove", "shutdown"}


class TaskRequest(BaseModel):
    task: str


def classify(task: str) -> str:
    words = task.lower().split()
    if any(kw in words for kw in DESTRUCTIVE_KEYWORDS):
        return "destructive"
    if len(words) > 40:
        return "complex"
    return "simple"


def execute(task: str) -> str:
    return f"Task received: {task}"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(request: TaskRequest):
    task = request.task.strip()
    classification = classify(task)

    if classification == "destructive":
        return {"status": "confirm_required", "task": task}

    result = execute(task)
    return {"status": "done", "result": result}
