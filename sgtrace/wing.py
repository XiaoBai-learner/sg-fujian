"""OntoWing 适配层：以库的方式调用 OntoWing 的纯领域代码。

只使用 app.domain 下不依赖 Django / 数据库 / 网络的模块：
  modeling_profiles.validate_editor         静态校验：本体、数据管道映射（字段字典、键与关联）、规则与约束
  modeling_artifacts.projection.render_member  导出 ontology.ttl（OWL）、mapping.ttl（R2RML）、rules.ttl（SWRL）

不走 OntoWing HTTP 服务：它需要 Manager 签发的 JWT、角色绑定文件和 MySQL 业务库，本地无法独立运行。
"""
import json
import subprocess
import sys
from functools import lru_cache

from .config import ontowing_backend

MODEL_ID = "5f0c2a8e-7b1d-4c3e-9a6f-2d8b4e1c0a01"   # 本地固定的模型标识（Wing 校验需要）


class WingUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _modules():
    backend = ontowing_backend()
    if not (backend / "app" / "domain" / "modeling_profiles.py").exists():
        raise WingUnavailable(f"找不到 OntoWing 后端：{backend}（可用环境变量 ONTOWING_BACKEND 指定）")
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.domain import modeling_profiles
    from app.domain.modeling_artifacts import projection
    return modeling_profiles, projection


def info():
    backend = ontowing_backend()
    commit = ""
    try:
        commit = subprocess.run(["git", "-C", str(backend), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        _modules()
        ok, err = True, ""
    except WingUnavailable as e:
        ok, err = False, str(e)
    return {"backend": str(backend), "commit": commit, "available": ok, "error": err}


def _bytes(obj):
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def validate_model(model):
    mp, _ = _modules()
    return mp.validate_editor(_bytes(model), "model")


def validate_pipeline(pipeline, model, snapshots):
    mp, _ = _modules()
    return mp.validate_editor(_bytes(pipeline), "pipeline", model=_bytes(model), model_id=MODEL_ID,
                              fact_plane_snapshots=_bytes(snapshots))


def validate_rules(rules, model):
    mp, _ = _modules()
    return mp.validate_editor(_bytes(rules), "rules", model=_bytes(model))


def render(kind, editor, model=None):
    """返回 (内容文本, 路径, profile, 导出损失列表)。"""
    _, pj = _modules()
    out = pj.render_member(kind, editor, MODEL_ID, model=model)
    content = out["content"]
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return content, out["path"], out["profile"], list(out.get("losses") or [])


ALITA_NS = "https://vocab.alita.dev/gongshang/"
