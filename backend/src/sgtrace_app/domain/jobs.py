"""Job state values shared by repositories and workers."""
JOB_STATES = frozenset({"pending", "running", "succeeded", "failed", "cancelled"})


def ensure_job_state(value: str) -> str:
    if value not in JOB_STATES:
        raise ValueError(f"unsupported job state: {value}")
    return value
