from sgtrace_app.modules.sources.metadata.reader import parse_mysql_ddl


def test_parse_mysql_ddl_preserves_comments_keys_and_types():
    ddl = """
    CREATE TABLE yx186.C_CONS (
      CONS_ID BIGINT NOT NULL COMMENT '客户标识',
      CONS_NO VARCHAR(30) NOT NULL COMMENT '户号',
      CONTRACT_CAP DECIMAL(12, 2) COMMENT '合同容量',
      PRIMARY KEY (CONS_ID),
      UNIQUE KEY uk_cons_no (CONS_NO)
    ) COMMENT='用电客户';
    """
    tables = parse_mysql_ddl(ddl)
    assert tables[0].schema == "yx186"
    assert tables[0].name == "C_CONS"
    assert tables[0].comment == "用电客户"
    assert tables[0].primary_key == ("CONS_ID",)
    assert tables[0].columns[1].comment == "户号"
    assert tables[0].columns[2].data_type == "decimal"


def test_parse_mysql_ddl_rejects_unbalanced_statement():
    import pytest
    with pytest.raises(ValueError, match="parse"):
        parse_mysql_ddl("CREATE TABLE yx186.BAD (ID INT")


def test_multiple_tables_use_schema_and_inline_key_preserve_exact_structure():
    tables = parse_mysql_ddl("""
        USE marketing;
        CREATE TABLE customers (id BIGINT PRIMARY KEY, name VARCHAR(30) COMMENT '姓名,称谓');
        CREATE TABLE marketing.bills (id INT NOT NULL, amount DECIMAL(12,2), PRIMARY KEY (id));
    """)
    assert [(table.schema, table.name) for table in tables] == [
        ("marketing", "customers"), ("marketing", "bills"),
    ]
    assert tables[0].primary_key == ("id",)
    assert tables[0].columns[0].nullable is False
    assert tables[0].columns[1].comment == "姓名,称谓"


def test_empty_ddl_cannot_create_a_successful_snapshot():
    import pytest
    with pytest.raises(ValueError):
        parse_mysql_ddl(" ")
