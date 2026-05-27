---
name: run-on-server
description: The app runs on a remote server, not locally. Don't try to run docker-compose or backend commands locally.
metadata:
  type: feedback
---

The app (docker-compose, backend, database) runs on a remote server, not the user's local machine. When the user needs to run commands or queries, provide the commands for them to copy and run — don't execute them locally.

**Why:** The user said "it runs on a server. Just gimme code to copy."

**How to apply:** Always provide copyable commands/SQL rather than running docker-compose/psql/backend commands directly.
