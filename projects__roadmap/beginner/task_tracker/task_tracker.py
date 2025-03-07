import sys
import json
import enum
import argparse
from typing import TypedDict, Union, List
from datetime import datetime


class TaskStatus(enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


COMMAND_STATUS_TO_TASK_STATUS = {
    'todo': TaskStatus.TODO,
    'in-progress': TaskStatus.IN_PROGRESS,
    'done': TaskStatus.DONE,
}


class Task:
    def __init__(self,
                 description: str,
                 status: TaskStatus,
                 created_at: Union[str | datetime],
                 updated_at:  Union[str | datetime],
                 id: Union[str | int] = None):
        self.id: int = int(id) if id else None
        self.description: str = description
        self.status: TaskStatus = status if isinstance(status, TaskStatus) else TaskStatus[status]
        self.created_at: datetime = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        self.updated_at: datetime = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S")

    def __str__(self):
        return f"ID: {self.id} | description: {self.description} | status: {self.status.value} | created_at: {self.created_at} | updated_at: {self.updated_at}"

    def set_id(self, id):
        self.id = id
        return self

    @staticmethod
    def create(description, status: TaskStatus = TaskStatus.TODO):
        assert description, 'Description is required'
        assert status in TaskStatus, 'Unknow status'
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return Task(description, status, now, now)

    def to_json(self):
        return {
            "id": self.id,
            "description": self.description,
            "status": str(self.status.value),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }


class TaskStore:
    def __init__(self, store_name='store.json'):
        self.store_name = store_name
        self.last_id = 0
        self._load_db()

    class Database(TypedDict):
        last_id: int
        tasks: List[dict]

    def _load_db(self) -> 'TaskStore.Database':
        db: TaskStore.Database = {"last_id": 0, "tasks": []}
        try:
            with open(self.store_name, "r") as f:
                db = json.loads(f.read())
                self.last_id = db.get('last_id')
                return db
        except Exception:
            with open(self.store_name, "w") as f:
                f.write(json.dumps(db))
            return db

    def create(self, message: str) -> Task:
        return task_store.add(Task.create(message))

    def task(self, id) -> Task:
        tasks = self.tasks()
        return next((task for task in tasks if task.id == int(id)))

    def tasks(self) -> List[Task]:
        return [Task(**task) for task in self._load_db().get('tasks')]

    def filter(self, status:TaskStatus) -> List[Task]:
        if not status:
            return self.tasks()
        return [task for task in self.tasks() if task.status == status]

    def _update_all(self, tasks: List[Task]):
        with open(self.store_name, "w") as f:
            f.write(json.dumps({"last_id": self.last_id,
                    "tasks": [task.to_json() for task in tasks]}))

    def add(self, task: Task) -> Task:
        tasks = self.tasks()
        self.last_id = self.last_id + 1
        tasks.append(task.set_id(self.last_id))
        self._update_all(tasks)
        return task

    def _update(self, id, task: Task) -> Task:
        tasks = self.tasks()
        task_index = next(
            (i for i, task in enumerate(tasks) if task.id == id), -1)
        if task_index == -1:
            raise ValueError(f"ID: {id} doesn't exists")
        task.id = id
        task.updated_at = datetime.strptime(datetime.now(), "%Y-%m-%d %H:%M:%S")
        tasks[task_index] = task
        self._update_all(tasks)
        return task

    def update_status(self, id, status: TaskStatus) -> Task:
        task = self.task(id)
        task.status = status
        return self._update(id, task)

    def update_description(self, id, description: str) -> Task:
        task = self.task(id)
        task.description = description
        return self._update(id, task)

    def remove(self, id):
        tasks = self.tasks()
        task_index = next(
            (i for i, task in enumerate(tasks) if task.id == id), -1)
        if task_index == -1:
            raise ValueError(f"ID: {id} doesn't exists")
        tasks.pop(task_index)
        self._update_all(tasks)


class ExitWithMessage:
    def __init__(self, message: str):
        print(message)
        sys.exit()


def is_valid_id(id_message_or_status):
    try:
        int(id_message_or_status)
        return True
    except Exception as e:
        return False



if __name__ == "__main__":
    """
    Available commands:
        add <description:str>
        update <id:int> <description:str>
        delete <id:int>
        mark-in-progress <id:int>
        mark-done <id:int>
        list <status:done|todo|in-progress>
    """
    AVAILABLE_COMMANDS = ['add', 'update', 'delete', 'mark', 'mark', 'list']
    AVAILABLE_STATUS = ['done', 'todo', 'in-progress']


    parser = argparse.ArgumentParser(description="Task Manager")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Command to execute")

    # Add command
    parser_add = subparsers.add_parser("add", help="Add a new task")
    parser_add.add_argument("description", nargs="+", help="Task description")

    # Update command
    parser_update = subparsers.add_parser("update", help="Update an existing task")
    parser_update.add_argument("id", type=int, help="ID of the task to update")
    parser_update.add_argument("description", nargs="+", help="New task description")

    # Delete command
    parser_delete = subparsers.add_parser("delete", help="Delete a task")
    parser_delete.add_argument("id", type=int, help="ID of the task to delete")

    # Mark-in-progress command
    parser_mark_in_progress = subparsers.add_parser("mark-in-progress", help="Mark a task as in progress")
    parser_mark_in_progress.add_argument("id", type=int, help="ID of the task")

    # Mark-done command
    parser_mark_done = subparsers.add_parser("mark-done", help="Mark a task as done")
    parser_mark_done.add_argument("id", type=int, help="ID of the task")

    # List command
    parser_list = subparsers.add_parser("list", help="List tasks by status")
    parser_list.add_argument("status", nargs="?", choices=["done", "todo", "in-progress", "all"], default="all",
                             help="(Optional) Status of tasks to list. Defaults to 'all'.")

    args = parser.parse_args()

    command = args.command
    # Convert description from list to string if applicable
    description = " ".join(args.description) if hasattr(args, "description") else ""

    task_store = TaskStore()

    match command:
        case 'add':
            task = task_store.create(description)
            ExitWithMessage(f'Task created: {task}')

        case 'update':
            task = task_store.update_description(args.id, description)
            ExitWithMessage(f'Task updated: {task}')

        case 'delete':
            task_store.remove(args.id)

        case 'mark-in-progress':
            task = task_store.update_status(args.id, TaskStatus.IN_PROGRESS)
            ExitWithMessage(f'Task updated: {task}')

        case 'mark-done':
            task = task_store.update_status(args.id, TaskStatus.IN_PROGRESS)
            ExitWithMessage(f'Task updated: {task}')

        case 'list':
            tasks = task_store.filter(COMMAND_STATUS_TO_TASK_STATUS.get(args.status))
            ExitWithMessage('\n'.join([str(task) for task in tasks]))

        case _:
            ExitWithMessage(f'[ERROR] Unknow command {command}')