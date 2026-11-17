"""Run OntoWing pure-domain validation/export in an isolated child interpreter."""
import json
import os
from pathlib import Path
import subprocess
import sys


def compile_model(draft, tables):
    root = Path(__file__).resolve().parents[5]
    backend = Path(os.environ.get('ONTOWING_BACKEND', root.parent / 'ontowing/backend')).resolve()
    if not (backend / 'app/domain/modeling_profiles.py').is_file():
        raise ValueError('OntoWing 领域库不可用，请配置 ONTOWING_BACKEND')
    raw = json.dumps({'draft':draft,'tables':tables},ensure_ascii=False).encode()
    if len(raw)>15_000_000: raise ValueError('模型超过当前导出容量')
    try:
        process = subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('worker.py')),str(backend)],
                                 input=raw,capture_output=True,timeout=25,env={'LANG':'C.UTF-8'})
    except subprocess.TimeoutExpired as error: raise ValueError('OntoWing 校验导出超时') from error
    if process.returncode or len(process.stdout)>15_000_000:
        raise ValueError('OntoWing 校验导出失败，请查看服务端诊断')
    result=json.loads(process.stdout)
    if 'error' in result: raise ValueError('OntoWing 输入不兼容：'+result['error'])
    return result
