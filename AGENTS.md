# Project context

Do not automatically read the root `.env`, files in `docs/`, or other project
reference documents. Read them only when the user explicitly invokes the
`Read docs` task, for example by saying `Run Read docs`. The task definition is
in `tasks/read-docs.md`; read and execute it when invoked. Merely starting a
session or receiving a development request does not invoke this task.

This restriction does not prevent reading source code, tests, configuration
needed for an implementation, or applicable AGENTS.md instructions. If a task
needs reference documentation that has not been authorized, ask the user to
invoke `Read docs` rather than opening the documents automatically.

Treat environment variable values as potentially sensitive. Do not reproduce
them in replies, logs, commits, or documentation. The `.env` file is local and
must remain excluded from Git.

The current development focus is the backend. Use the `backend` branch for
backend work and the `frontend` branch for frontend work. Do not switch branches
without a task that calls for it.

Database is located in data/astronautas.db