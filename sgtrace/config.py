"""运行配置：路径、MySQL 连接、OntoWing 位置。

MySQL 凭据只从环境变量或项目根目录 .env 读取（.env 已 gitignore），不写入代码和产物。
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
INPUTS = DATA / "inputs"          # 流水线只允许读这里
SANDBOX = DATA / "sandbox"        # 带数据的 SQLite，仅用于 R2RML 执行校验
ARTIFACTS = ROOT / "artifacts"    # 构建产物
WEB = ROOT / "web"

SOURCE_DBS = ("yx186", "cjxt", "kf95598")
PLATFORM_DB = "sgfj_dataplatform"
SYSTEM_TITLES = {"yx186": "营销业务应用系统", "cjxt": "用电信息采集系统", "kf95598": "95598客服系统",
                 PLATFORM_DB: "数据中台"}


def _load_dotenv():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


_load_dotenv()


@dataclass(frozen=True)
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str

    @property
    def display(self):
        return f"{self.user}@{self.host}:{self.port}"


def mysql_config():
    """返回 MySQLConfig；未配置用户名时返回 None（服务会退回读 DDL 文件）。"""
    user = os.environ.get("MYSQL_USER")
    if not user:
        return None
    return MySQLConfig(host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
                       port=int(os.environ.get("MYSQL_PORT", "3306")),
                       user=user, password=os.environ.get("MYSQL_PASSWORD", ""))


def ontowing_backend():
    return Path(os.environ.get("ONTOWING_BACKEND", str(ROOT.parent / "ontowing" / "backend"))).resolve()
