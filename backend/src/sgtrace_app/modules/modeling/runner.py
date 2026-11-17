"""Isolate parser/optional provider work from the API process with a hard deadline."""
import json
import os
from pathlib import Path
import subprocess
import sys


def analyze(materials,semantic=False):
    environment={'LANG':'C.UTF-8',**{k:os.environ[k] for k in ('LLM_BASE_URL','LLM_MODEL','LLM_API_KEY') if k in os.environ}}
    try:
        process=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('engine_worker.py'))],
            input=json.dumps({'materials':materials,'semantic':semantic},ensure_ascii=False).encode(),
            capture_output=True,timeout=90,env=environment)
    except subprocess.TimeoutExpired as error: raise ValueError('建模分析超过 90 秒，已停止本轮；模型调用可能已计费，不会自动重试。') from error
    if process.returncode or len(process.stdout)>30_000_000: raise ValueError('建模解析进程失败或结果超过当前容量')
    value=json.loads(process.stdout)
    if 'error' in value: raise ValueError(value['error'])
    return value
