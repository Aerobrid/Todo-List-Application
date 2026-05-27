from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import Category, Priority, SubTask, Task, SubTaskCreate, TaskCreate, TaskUpdate

# --- TASK CRUD OPERATIONS ---

def get_task_by_id(db: Session, task_id: int) -> Optional[Task]:
    """
    Retrieves a single task database record by its primary key.
    Returns None if the record does not exist.
    """
    return db.query(Task).filter(Task.id == task_id).first()

def get_all_tasks(
    db: Session, 
    is_completed: Optional[bool] = None, 
    search_query: Optional[str] = None
) -> List[Task]:
    """
    Queries all tasks, supporting filters for completion status and search keywords.
    Orders tasks: incomplete tasks first, sorted by created_at descending.
    """
    query = db.query(Task)
    
    if is_completed is not None:
        query = query.filter(Task.is_completed == is_completed)
        
    if search_query:
        # icontains-like behavior: checks case-insensitive match on title or description
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Task.title.like(search_pattern),
                Task.description.like(search_pattern)
            )
        )
        
    return query.order_by(Task.is_completed.asc(), Task.created_at.desc()).all()

def create_task(db: Session, task_in: TaskCreate) -> Task:
    """
    Constructs a new task record. Parses nested subtask creations if provided.
    Saves and commits changes to SQLite transactional log.
    """
    # extract subtasks if they exist prior to saving the parent model
    subtask_data = task_in.subtasks or []
    
    db_task = Task(
        title=task_in.title,
        description=task_in.description,
        is_completed=task_in.is_completed,
        priority=task_in.priority,
        category=task_in.category,
        due_date=task_in.due_date,
        completed_at=datetime.now(timezone.utc) if task_in.is_completed else None
    )
    
    db.add(db_task)
    db.flush()  # flushes session state to assign task.id for relational child models

    # create nested subtasks in the same transaction unit
    for sub_item in subtask_data:
        db_sub = SubTask(
            task_id=db_task.id,
            title=sub_item.title,
            is_completed=sub_item.is_completed
        )
        db.add(db_sub)
        
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, db_task: Task, task_in: TaskUpdate) -> Task:
    """
    Updates attributes on a task model using partial parameters.
    Automatically assigns completed_at timestamps when completed state toggles.
    """
    update_data = task_in.model_dump(exclude_unset=True)
    
    # handle timestamp tracking if status changes
    if "is_completed" in update_data:
        new_status = update_data["is_completed"]
        # guard against updating timestamp unnecessarily if state is unchanged
        if new_status != db_task.is_completed:
            db_task.completed_at = datetime.now(timezone.utc) if new_status else None
            # Cascade completion: synchronize completion status of parent to all child subtasks
            for subtask in db_task.subtasks:
                subtask.is_completed = new_status
            
    for field, value in update_data.items():
        # Do not allow setting NOT NULL database columns (title, priority, category) to None
        if field in ["title", "priority", "category"] and value is None:
            continue
        setattr(db_task, field, value)
        
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int) -> bool:
    """
    Deletes a task by ID. Returns True if task existed and was deleted,
    False if the task did not exist.
    """
    db_task = get_task_by_id(db, task_id)
    if db_task is None:
        return False
        
    db.delete(db_task)
    db.commit()
    return True

def clear_completed_tasks(db: Session) -> int:
    """
    Bulk removes all tasks marked as completed.
    Returns the count of deleted task rows.
    """
    completed_tasks = db.query(Task).filter(Task.is_completed == True).all()
    count = len(completed_tasks)
    
    if count == 0:
        return 0
        
    for task in completed_tasks:
        db.delete(task)
        
    db.commit()
    return count


# --- SUBTASK CRUD OPERATIONS ---

def get_subtask_by_id(db: Session, subtask_id: int) -> Optional[SubTask]:
    """
    Fetches a single subtask by its primary key.
    """
    return db.query(SubTask).filter(SubTask.id == subtask_id).first()

def create_subtask(db: Session, task_id: int, subtask_in: SubTaskCreate) -> SubTask:
    """
    Appends a new subtask to an existing parent task.
    """
    db_sub = SubTask(
        task_id=task_id,
        title=subtask_in.title,
        is_completed=subtask_in.is_completed
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

def update_subtask_status(db: Session, db_subtask: SubTask, is_completed: bool) -> SubTask:
    """
    Toggles completion status for a subtask record.
    """
    db_subtask.is_completed = is_completed
    db.commit()
    db.refresh(db_subtask)
    return db_subtask

def delete_subtask(db: Session, subtask_id: int) -> bool:
    """
    Deletes a subtask by ID. Returns True if found and deleted, False otherwise.
    """
    db_sub = get_subtask_by_id(db, subtask_id)
    if db_sub is None:
        return False
        
    db.delete(db_sub)
    db.commit()
    return True
