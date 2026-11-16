"""本体建模：材料识别、本体编辑、R2RML、校验与采用快照。"""
from fastapi import APIRouter

router = APIRouter(prefix="/modeling", tags=["modeling"])
