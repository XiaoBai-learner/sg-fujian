from uuid import uuid4
from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from ...infrastructure.db.models import Base

class TraceAttachment(Base):
    __tablename__='trace_attachments'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(String(36),nullable=False)
    content_uri: Mapped[str]=mapped_column(Text,nullable=False)
    content_type: Mapped[str]=mapped_column(String(40),nullable=False)
    size_bytes: Mapped[int]=mapped_column(Integer,nullable=False)
