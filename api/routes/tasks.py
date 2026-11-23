from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from api.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Asynchronous Tasks"])

@router.get("/{task_id}")
def get_task_status(task_id: str):
    """
    Poll the status of an asynchronous background task.
    Returns task state: PENDING, PROGRESS, SUCCESS, or FAILURE.
    """
    res = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "state": res.state,
    }

    if res.state == "PROGRESS":
        response["meta"] = res.info
    elif res.state == "SUCCESS":
        response["result"] = res.result
    elif res.state == "FAILURE":
        response["error"] = str(res.result)

    return response
