# Bridge

Bridge is a FastAPI backend for an accounting research and workflow product.
It uses a clean monolith with strict service and repository boundaries so the
API stays easy to reason about while the domain grows.

## What It Covers

- creating and listing workspaces
- attaching users to workspaces with roles
- registering documents
- creating research requests
- creating AI jobs for research requests
- tracking AI job status transitions
- listing workspace activity

## Architecture Notes

The service layer owns business rules and audit-event generation. Repositories
stay focused on database access, and request schemas define API contracts.

AI job behavior now lives in a dedicated `AIJobService`, but it still runs in
the same web process as the rest of the API.

### Tradeoff

I intentionally did not move AI job handling into a separate worker yet.

That choice keeps the implementation simpler for this stage:

- status transitions and audit writes happen in one transaction path
- there is no queueing or cross-process orchestration overhead
- the code is easier to test end to end inside the API process

The downside is that job execution is still synchronous from the API’s point of
view, so the process is responsible for both request handling and job lifecycle
management. If the job runner needs to scale independently, a worker boundary
would be the next step.

## Run

```bash
uv sync
just run
```

## Verify

```bash
just lint
just format
just check
```
