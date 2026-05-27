from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app import crud
from app.database import get_db
from app.models import (
    SubTaskCreate,
    SubTaskResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    Task,
)
from app.security import read_rate_limiter, sanitize_string, write_rate_limiter

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# --- TASK CONTROLLERS ---

@router.get(
    "/", 
    response_model=List[TaskResponse], 
    dependencies=[Depends(read_rate_limiter)]
)
def read_tasks(
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    search: Optional[str] = Query(None, description="Search tasks by keyword"),
    db: Session = Depends(get_db)
 ) -> List[Task]:
    """
    Returns list of tasks. Sanitizes search parameter to prevent DB search exploits.
    Supports filtering and full text searches.
    """
    sanitized_search = sanitize_string(search)
    return crud.get_all_tasks(db, is_completed=is_completed, search_query=sanitized_search)

@router.get(
    "/{task_id}", 
    response_model=TaskResponse, 
    dependencies=[Depends(read_rate_limiter)]
)
def read_task(task_id: int, db: Session = Depends(get_db)) -> Task:
    """
    Retrieves details for a single task. Uses a guard clause for absent IDs.
    """
    db_task = crud.get_task_by_id(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    return db_task

@router.post(
    "/", 
    response_model=TaskResponse, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(write_rate_limiter)]
)
def add_task(task_in: TaskCreate, db: Session = Depends(get_db)) -> Task:
    """
    Creates a new task. Strings are sanitized to prevent XSS.
    """
    sanitized_title = sanitize_string(task_in.title)
    if not sanitized_title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Task title cannot be empty or whitespace-only"
        )
    task_in.title = sanitized_title

    if task_in.description:
        task_in.description = sanitize_string(task_in.description)
        
    if task_in.subtasks:
        for subtask in task_in.subtasks:
            sanitized = sanitize_string(subtask.title)
            if not sanitized:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Subtask title cannot be empty or whitespace-only"
                )
            subtask.title = sanitized

    return crud.create_task(db=db, task_in=task_in)

@router.put(
    "/{task_id}", 
    response_model=TaskResponse, 
    dependencies=[Depends(write_rate_limiter)]
)
def modify_task(
    task_id: int, 
    task_in: TaskUpdate, 
    db: Session = Depends(get_db)
) -> Task:
    """
    Updates fields on a task. Guard clause returns 404 early if ID is missing.
    """
    db_task = crud.get_task_by_id(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )

    # sanitize inbound strings if updated
    if task_in.title is not None:
        sanitized_title = sanitize_string(task_in.title)
        if not sanitized_title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Task title cannot be empty or whitespace-only"
            )
        task_in.title = sanitized_title

    if task_in.description is not None:
        task_in.description = sanitize_string(task_in.description)

    return crud.update_task(db=db, db_task=db_task, task_in=task_in)

@router.delete(
    "/{task_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(write_rate_limiter)]
)
def remove_task(task_id: int, db: Session = Depends(get_db)) -> None:
    """
    Deletes task. Throws 404 if database record does not exist.
    """
    deleted = crud.delete_task(db, task_id=task_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found"
        )
    return None

@router.post(
    "/clear-completed", 
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(write_rate_limiter)]
)
def clear_completed(db: Session = Depends(get_db)) -> dict:
    """
    Bulk deletes completed tasks. Returns number of records purged.
    """
    deleted_count = crud.clear_completed_tasks(db)
    return {
        "message": f"Successfully cleared completed tasks",
        "count": deleted_count
    }


# --- SUBTASK CONTROLLERS ---

@router.post(
    "/{task_id}/subtasks", 
    response_model=SubTaskResponse, 
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(write_rate_limiter)]
)
def add_subtask(
    task_id: int, 
    subtask_in: SubTaskCreate, 
    db: Session = Depends(get_db)
) -> SubTaskResponse:
    """
    Adds a checklist subtask to a task. Verifies parent task existence first.
    """
    db_task = crud.get_task_by_id(db, task_id=task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parent Task with ID {task_id} not found"
        )
        
    sanitized = sanitize_string(subtask_in.title)
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subtask title cannot be empty or whitespace-only"
        )
    subtask_in.title = sanitized
    return crud.create_subtask(db=db, task_id=task_id, subtask_in=subtask_in)

@router.put(
    "/subtasks/{subtask_id}", 
    response_model=SubTaskResponse, 
    dependencies=[Depends(write_rate_limiter)]
)
def toggle_subtask(
    subtask_id: int, 
    is_completed: bool = Query(..., description="Toggle completion status"),
    db: Session = Depends(get_db)
) -> SubTaskResponse:
    """
    Toggles completion of a subtask.
    """
    db_sub = crud.get_subtask_by_id(db, subtask_id=subtask_id)
    if db_sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subtask with ID {subtask_id} not found"
        )
        
    return crud.update_subtask_status(db=db, db_subtask=db_sub, is_completed=is_completed)

@router.delete(
    "/subtasks/{subtask_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(write_rate_limiter)]
)
def remove_subtask(subtask_id: int, db: Session = Depends(get_db)) -> None:
    """
    Deletes a subtask. Throws 404 if record doesn't exist.
    """
    deleted = crud.delete_subtask(db, subtask_id=subtask_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subtask with ID {subtask_id} not found"
        )
    return None
