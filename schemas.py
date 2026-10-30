
TOOLS = [
    {
        "name": "get_tasks",
        "description": (
            "Retrieve all outstanding tasks "
            "that have not been completed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Retrieve upcoming calendar events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_task",
        "description": (
            "Create a new task with a title "
            "and due date. Use only when "
            "the user explicitly requests "
            "task creation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title",
                },
                "due_date": {
                    "type": "string",
                    "description": (
                        "Due date in YYYY-MM-DD format"
                    ),
                },
            },
            "required": [
                "title",
                "due_date",
            ],
        },
    },
]
