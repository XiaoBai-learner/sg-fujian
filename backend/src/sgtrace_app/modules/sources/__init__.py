"""数据源接入：只读连接、元数据、统一材料与血缘证据。"""
from fastapi import APIRouter

router = APIRouter(prefix="/sources", tags=["sources"])
