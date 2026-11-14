# Read docs

## Invocation

Run this task only when the user explicitly requests `Run Read docs` (or
explicitly asks to execute this task). Do not execute it automatically.

## Steps

1. Read the commented requirements and conversation context in the root `.env`,
   if present. Extract only comment lines; do not display environment variable
   values. Ignore TODO placeholders.
2. List the reference documents in `docs/`. Read the documents the user names;
   if no subset is specified, read all supported documents in that directory.
   Do not follow external links or read documents outside that scope unless
   the user explicitly includes them.
3. Summarize the requirements, decisions, constraints, and next tasks. Report
   conflicts or unreadable documents without inventing missing information.
4. Use the resulting context for the current conversation. Do not modify code,
   requirements, or documentation as part of this reading task.

## Scope of permission

An invocation authorizes one reading pass. It does not enable automatic reading
in future sessions or rereading changed documents. Ask for another invocation
when a fresh reading is needed.
