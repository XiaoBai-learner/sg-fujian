from sgtrace_app.modules.sources.lineage.parser import LineageParser


def test_lineage_parser_extracts_projection_and_expression_dependencies():
    parsed = LineageParser().parse("""
      INSERT INTO ads_yx_qfmx_cx
      SELECT r.CONS_NO, r.RCVBL_AMT - r.RCVED_AMT AS ARREARS_AMT
      FROM yx186.A_RCVBL_FLOW r
      WHERE r.SETTLE_FLAG = '0'
    """)
    assert ("yx186.A_RCVBL_FLOW", "CONS_NO") in parsed.references
    assert ("yx186.A_RCVBL_FLOW", "RCVBL_AMT") in parsed.references
    assert parsed.outputs["ARREARS_AMT"].kind == "calculated"


def test_lineage_parser_returns_empty_for_non_sql_text():
    assert LineageParser().parse("this is not SQL").outputs == {}
