from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import JobModel


class JobRepository:
    def __init__(self, session: AsyncSession, lease_seconds: int = 60):
        self.session = session
        self.lease_seconds = lease_seconds

    async def enqueue(self, kind: str, payload: dict, idempotency_key: str) -> JobModel:
        job = JobModel(id=str(uuid4()), kind=kind, status="pending", payload_json=payload, idempotency_key=idempotency_key)
        self.session.add(job)
        await self.session.flush()
        return job

    async def claim_next(self, worker_id: str) -> JobModel | None:
        now = datetime.now(timezone.utc)
        candidate = await self.session.scalar(select(JobModel).where(
            ((JobModel.status == "pending") | ((JobModel.status == "running") & (JobModel.lease_until < now))),
        ).order_by(JobModel.created_at).limit(1).with_for_update())
        if candidate is None:
            return None
        candidate.status = "running"
        candidate.lease_owner = worker_id
        candidate.lease_until = now + timedelta(seconds=self.lease_seconds)
        candidate.attempts += 1
        await self.session.flush()
        return candidate

    async def complete(self, job_id: str, result_ref: str) -> None:
        await self.session.execute(update(JobModel).where(JobModel.id == job_id).values(
            status="succeeded", result_ref=result_ref, lease_owner=None, lease_until=None,
        ))

    async def fail(self, job_id: str, code: str, detail: str) -> None:
        await self.session.execute(update(JobModel).where(JobModel.id == job_id).values(
            status="failed", error_code=code, error_detail=detail, lease_owner=None, lease_until=None,
        ))

    async def cancel(self, job_id: str) -> None:
        await self.session.execute(update(JobModel).where(JobModel.id == job_id).values(
            status="cancelled", lease_owner=None, lease_until=None,
        ))
