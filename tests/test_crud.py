from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app import crud
from app.models import Category, Priority, SubTaskCreate, TaskCreate, TaskUpdate

def test_create_task(db_session: Session) -> None:
    """
    Asserts a task can be constructed and saved, checking automatic default values.
    """
    task_in = TaskCreate(
        title="Check system logs",
        description="Verify backend memory allocations",
        priority=Priority.HIGH,
        category=Category.WORK
    )
    
    task = crud.create_task(db_session, task_in=task_in)
    
    assert task.id is not None
    assert task.title == "Check system logs"
    assert task.description == "Verify backend memory allocations"
    assert task.priority == Priority.HIGH
    assert task.category == Category.WORK
    assert task.is_completed is False
    assert task.completed_at is None
    assert isinstance(task.created_at, datetime)

def test_task_completion_timestamps(db_session: Session) -> None:
    """
    Verifies that completed_at timestamps are written only when tasks transition to True.
    """
    # 1. Create incomplete task
    task_in = TaskCreate(title="Deploy container", description=None)
    task = crud.create_task(db_session, task_in=task_in)
    assert task.is_completed is False
    assert task.completed_at is None
    
    # 2. Toggle to True
    update_in = TaskUpdate(is_completed=True, title=None, description=None)
    updated = crud.update_task(db_session, db_task=task, task_in=update_in)
    assert updated.is_completed is True
    assert updated.completed_at is not None
    assert isinstance(updated.completed_at, datetime)
    
    # 3. Toggle back to False
    update_in_false = TaskUpdate(is_completed=False, title=None, description=None)
    updated_false = crud.update_task(db_session, db_task=updated, task_in=update_in_false)
    assert updated_false.is_completed is False
    assert updated_false.completed_at is None

def test_create_task_with_subtasks(db_session: Session) -> None:
    """
    Validates atomic nesting of subtasks during creation phase.
    """
    task_in = TaskCreate(
        title="Bake Bread",
        description=None,
        subtasks=[
            SubTaskCreate(title="Buy flour"),
            SubTaskCreate(title="Knead dough")
        ]
    )
    task = crud.create_task(db_session, task_in=task_in)
    
    assert task.id is not None
    assert len(task.subtasks) == 2
    assert task.subtasks[0].title == "Buy flour"
    assert task.subtasks[1].title == "Knead dough"
    assert task.subtasks[0].is_completed is False

def test_cascade_delete_subtasks(db_session: Session) -> None:
    """
    Confirms child subtask instances are automatically expunged from the database
    when the parent task model is removed.
    """
    task_in = TaskCreate(
        title="Setup CI pipeline",
        description=None,
        subtasks=[SubTaskCreate(title="Write GHA workflow file")]
    )
    task = crud.create_task(db_session, task_in=task_in)
    task_id = task.id
    subtask_id = task.subtasks[0].id
    
    # Assert records exist
    assert crud.get_subtask_by_id(db_session, subtask_id) is not None
    
    # Delete parent
    deleted = crud.delete_task(db_session, task_id)
    assert deleted is True
    
    # Assert child is purged automatically (cascade delete constraint)
    assert crud.get_task_by_id(db_session, task_id) is None
    assert crud.get_subtask_by_id(db_session, subtask_id) is None

def test_clear_completed_tasks(db_session: Session) -> None:
    """
    Verifies that bulk clearing removes only completed tasks.
    """
    # Create completed task
    t1 = crud.create_task(db_session, TaskCreate(title="Task A", description=None, is_completed=True))
    # Create active task
    t2 = crud.create_task(db_session, TaskCreate(title="Task B", description=None, is_completed=False))
    
    cleared_count = crud.clear_completed_tasks(db_session)
    assert cleared_count == 1
    
    assert crud.get_task_by_id(db_session, t1.id) is None
    assert crud.get_task_by_id(db_session, t2.id) is not None

def test_task_complete_marks_subtasks_complete(db_session: Session) -> None:
    """
    Checks that when a parent task is set to is_completed=True, all its child
    subtask rows are automatically updated to is_completed=True, and if toggled
    back to is_completed=False, all child subtasks are also set to False.
    """
    task_in = TaskCreate(
        title="Check system configs",
        description=None,
        subtasks=[
            SubTaskCreate(title="Locate build dependencies"),
            SubTaskCreate(title="Audit configuration properties")
        ]
    )
    task = crud.create_task(db_session, task_in=task_in)
    
    # verify initially incomplete
    assert task.subtasks[0].is_completed is False
    assert task.subtasks[1].is_completed is False
    
    # toggle parent task to complete
    update_in = TaskUpdate(is_completed=True, title=None, description=None)
    updated = crud.update_task(db_session, db_task=task, task_in=update_in)
    
    # assert child subtasks cascaded to complete
    assert updated.subtasks[0].is_completed is True
    assert updated.subtasks[1].is_completed is True

    # toggle parent task back to incomplete
    update_in_false = TaskUpdate(is_completed=False, title=None, description=None)
    updated_false = crud.update_task(db_session, db_task=updated, task_in=update_in_false)

    # assert child subtasks cascaded back to incomplete
    assert updated_false.subtasks[0].is_completed is False
    assert updated_false.subtasks[1].is_completed is False
