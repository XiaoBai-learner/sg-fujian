from datetime import datetime
from uuid import uuid4
from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME
from ...infrastructure.db.models import Base

class ModelingRun(Base):
    __tablename__='modeling_runs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False)
    request_key: Mapped[str]=mapped_column(String(36),unique=True,nullable=False)
    input_sha256: Mapped[str]=mapped_column(String(64),nullable=False)
    status: Mapped[str]=mapped_column(String(30),nullable=False)
    revision: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    input_json: Mapped[dict]=mapped_column(JSON,nullable=False)
    result_json: Mapped[dict | None]=mapped_column(JSON)
    validation_json: Mapped[dict | None]=mapped_column(JSON)
    error: Mapped[str | None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True).with_variant(DATETIME(fsp=6),"mysql"),server_default=func.now(),nullable=False)

class AdoptedModel(Base):
    __tablename__='adopted_models'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False)
    run_id: Mapped[str]=mapped_column(String(36),nullable=False)
    revision: Mapped[int]=mapped_column(Integer,nullable=False)
    snapshot_json: Mapped[dict]=mapped_column(JSON,nullable=False)
    artifacts_json: Mapped[dict]=mapped_column(JSON,nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True).with_variant(DATETIME(fsp=6),"mysql"),server_default=func.now(),nullable=False)
