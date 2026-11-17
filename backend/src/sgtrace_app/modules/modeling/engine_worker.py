import json
from pathlib import Path
import sys

if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
    from sgtrace_app.modules.modeling.engine import build_model
    from sgtrace_app.modules.modeling.semantics import enhance
    try:
        payload=json.loads(sys.stdin.buffer.read(10_000_001))
        result=build_model(payload['materials'])
        if payload['semantic']: enhance(result,payload['materials'])
    except ValueError as error: result={'error':str(error)[:500]}
    except Exception: result={'error':'建模解析失败，未生成可用结果。'}
    sys.stdout.write(json.dumps(result,ensure_ascii=False))
