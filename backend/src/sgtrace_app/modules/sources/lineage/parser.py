"""Bounded SQL dependency extraction; full DataWorks ingestion follows this contract."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class OutputColumn:
    name: str
    kind: str
    expression: str


@dataclass(frozen=True)
class ParsedLineage:
    references: frozenset[tuple[str, str]]
    outputs: dict[str, OutputColumn]


class LineageParser:
    _ref = re.compile(r"\b([\w]+)\.([\w]+)\b")

    def parse(self, sql: str) -> ParsedLineage:
        match = re.search(r"SELECT\s+(.*?)\s+FROM\s+([\w.]+)", sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return ParsedLineage(frozenset(), {})
        projection = match.group(1)
        aliases = {
            alias or table.split(".")[-1]: table
            for table, alias in re.findall(r"(?:FROM|JOIN)\s+([\w.]+)(?:\s+(?!WHERE\b|JOIN\b|ON\b)([\w]+))?", sql, re.IGNORECASE)
        }
        references = frozenset((aliases.get(table, table), column) for table, column in self._ref.findall(projection))
        outputs: dict[str, OutputColumn] = {}
        for item in projection.split(","):
            expression = item.strip()
            alias = re.search(r"\bAS\s+([\w]+)$", expression, re.IGNORECASE)
            if alias:
                name = alias.group(1)
                kind = "calculated" if re.search(r"[-+*/()]", expression) else "direct"
            else:
                name = expression.split(".")[-1].strip()
                kind = "direct"
            outputs[name] = OutputColumn(name, kind, expression)
        return ParsedLineage(references, outputs)
