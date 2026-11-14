"""Guards crops.json: no number without a source.

    python -m unittest test_crops

Fails if a numeric parameter has no source, if a source id is not listed in SOURCES.md,
or if a value is missing its locator or status.
"""
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).parent
STATUSES = {"verificat", "de_confirmat"}
VALUE_KEYS = {"value", "unit", "source", "locator", "status"}


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def walk(node, path):
    """Yields (path, kind, node): kind is 'value' for a sourced value, 'bare' for a number outside one."""
    if isinstance(node, dict):
        if "value" in node:
            yield path, "value", node
            return  # numbers inside a sourced value (value, engine_value) are covered by its source
        for key, child in node.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(node, list):
        for i, child in enumerate(node):
            yield from walk(child, f"{path}[{i}]")
    elif is_number(node):
        yield path, "bare", node


class CropsHaveSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((HERE / "crops.json").read_text(encoding="utf-8"))
        cls.known = set(re.findall(r"^## (S\d+)\b", (HERE / "SOURCES.md").read_text(encoding="utf-8"), re.M))
        cls.found = [(f"{c['id']}{p}", kind, node) for c in cls.data["crops"] for p, kind, node in walk(c, "")]

    def test_file_has_values(self):
        self.assertGreater(sum(kind == "value" for _, kind, _ in self.found), 50)

    def test_no_number_without_a_source(self):
        bare = [path for path, kind, _ in self.found if kind == "bare"]
        self.assertEqual(bare, [], "numbers written without {value, unit, source, locator, status}")

    def test_every_value_is_complete(self):
        problems = []
        for path, kind, node in self.found:
            if kind != "value":
                continue
            missing = [k for k in VALUE_KEYS if node.get(k) in (None, "")]
            if missing:
                problems.append(f"{path}: missing {', '.join(sorted(missing))}")
            elif node["source"] not in self.known:
                problems.append(f"{path}: source {node['source']} is not in SOURCES.md")
            elif node["status"] not in STATUSES:
                problems.append(f"{path}: status '{node['status']}'")
        self.assertEqual(problems, [])

    def test_ranges_say_what_the_engine_uses(self):
        """Where sources give a range for a threshold or a gap, the file must name the value the engine takes."""
        problems = []
        for path, kind, node in self.found:
            if kind == "value" and isinstance(node["value"], list) and all(is_number(x) for x in node["value"]):
                if any(part in path for part in (".rotation.", ".heat_at_flowering.")) and not is_number(node.get("engine_value")):
                    problems.append(path)
        self.assertEqual(problems, [], "ranges without engine_value")


if __name__ == "__main__":
    unittest.main()
