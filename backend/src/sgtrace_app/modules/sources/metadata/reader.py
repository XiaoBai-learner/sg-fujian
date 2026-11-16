"""DDL and connector metadata normalization."""
from dataclasses import dataclass
import re
import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    data_type: str
    comment: str
    nullable: bool
    position: int


@dataclass
class TableDefinition:
    schema: str
    name: str
    comment: str
    columns: tuple[ColumnDefinition, ...]
    primary_key: tuple[str, ...]
    unique_keys: tuple[tuple[str, ...], ...]


def _split_top_level(text: str) -> list[str]:
    result, current, depth, quote = [], [], 0, None
    for char in text:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if quote or depth != 0:
        raise ValueError("DDL parse failed: unbalanced quote or parenthesis")
    if "".join(current).strip():
        result.append("".join(current).strip())
    return result


def _unquote(value: str) -> str:
    return value.strip().strip("`\"")


def parse_mysql_ddl(text: str) -> list[TableDefinition]:
    tables: list[TableDefinition] = []
    current_schema = ""
    try:
        statements = sqlglot.parse(text, read="mysql")
    except sqlglot.errors.ParseError as error:
        raise ValueError("DDL parse failed: invalid SQL") from error
    for statement in statements:
        if isinstance(statement, exp.Use):
            current_schema = statement.this.name
            continue
        if not isinstance(statement, exp.Create) or statement.kind != "TABLE":
            continue
        schema = statement.this
        table = schema.this
        schema_name = table.db or current_schema
        table_name = table.name
        columns: list[ColumnDefinition] = []
        primary: list[str] = []
        uniques: list[tuple[str, ...]] = []
        for definition in schema.expressions:
            if isinstance(definition, exp.ColumnDef):
                constraints = definition.constraints or []
                comment = next(
                    (str(c.kind.this.name) for c in constraints if isinstance(c.kind, exp.CommentColumnConstraint)),
                    "",
                )
                nullable = not any(isinstance(c.kind, exp.NotNullColumnConstraint) for c in constraints)
                if any(isinstance(c.kind, exp.PrimaryKeyColumnConstraint) for c in constraints):
                    primary.append(definition.name)
                raw_type = definition.args["kind"].sql("mysql").lower()
                columns.append(ColumnDefinition(definition.name, raw_type.split("(", 1)[0], comment, nullable, len(columns)))
            elif isinstance(definition, exp.PrimaryKey):
                primary.extend(item.name for item in definition.expressions)
            elif isinstance(definition, exp.UniqueColumnConstraint):
                uniques.append(tuple(item.name for item in definition.this.expressions))
        table_comment = ""
        properties = statement.args.get("properties")
        if properties:
            table_comment = next(
                (str(prop.this.name) for prop in properties.expressions if isinstance(prop, exp.SchemaCommentProperty)),
                "",
            )
        tables.append(TableDefinition(
            schema_name,
            table_name,
            table_comment,
            tuple(columns),
            tuple(primary),
            tuple(uniques),
        ))
    if not tables:
        raise ValueError("DDL parse failed: no CREATE TABLE statement")
    for table in tables:
        if table.primary_key:
            table.columns = tuple(
                ColumnDefinition(c.name, c.data_type, c.comment, False if c.name in table.primary_key else c.nullable, c.position)
                for c in table.columns
            )
    return tables
