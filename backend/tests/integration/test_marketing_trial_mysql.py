import asyncio
import importlib.util
import os
from pathlib import Path

import pytest


@pytest.mark.skipif(os.environ.get("MYSQL_INTEGRATION") != "1", reason="requires installed local marketing trial")
def test_marketing_trial_gold_sql_and_like_queries_execute_on_mysql():
    path = Path(__file__).resolve().parents[3] / "trials/marketing_v1/run.py"
    spec = importlib.util.spec_from_file_location("marketing_trial_mysql", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = asyncio.run(module.verify_mysql())
    assert report["sql_equal"] == report["nonempty"] == report["checked_answers"] == 80
    assert report["hot_queries_executed"] == 22
