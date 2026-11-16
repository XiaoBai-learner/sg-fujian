"""Minimal DB-backed worker loop; domain handlers are registered by later tasks."""
from collections.abc import Awaitable, Callable


class JobRunner:
    def __init__(self, handlers: dict[str, Callable[[dict], Awaitable[str]]]):
        self.handlers = handlers

    async def run_once(self, job_kind: str, payload: dict) -> str:
        handler = self.handlers.get(job_kind)
        if handler is None:
            raise ValueError(f"no handler registered for job kind: {job_kind}")
        return await handler(payload)
