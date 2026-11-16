"""字段溯源智能体：需求理解、受控工具、来源判定与结果依据。"""
from fastapi import APIRouter

router = APIRouter(prefix="/agent", tags=["agent"])
