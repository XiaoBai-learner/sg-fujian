"""Stable error helpers for the versioned API."""
from fastapi import HTTPException


def not_implemented(code: str = "not_implemented") -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": "该业务接口尚未实现"})
