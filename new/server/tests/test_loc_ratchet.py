"""The size ratchet (scripts/loc_ratchet.py) checks long functions and big files, not every line added."""
import importlib.util
import os

_SPEC = importlib.util.spec_from_file_location(
    "loc_ratchet", os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "loc_ratchet.py"))
ratchet = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ratchet)


def _func(name, body_lines, indent=""):
    return f"{indent}def {name}():\n" + "".join(f"{indent}    x = {i}\n" for i in range(body_lines - 1))


def _tree(tmp_path, files):
    for rel, text in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return ratchet.measure(str(tmp_path))


def test_small_files_may_grow_and_short_functions_pass(tmp_path):
    files, functions = _tree(tmp_path, {"routes/a.py": _func("f", 40) + _func("g", 150)})
    assert ratchet.check(files, functions, {"files": {}, "functions": {}}) == []


def test_a_new_long_function_fails(tmp_path):
    files, functions = _tree(tmp_path, {"services/b.py": _func("long_one", 151)})
    problems = ratchet.check(files, functions, {"files": {}, "functions": {}})
    assert problems == ["services/b.py::long_one: function has 151 lines (limit 150)"]


def test_a_recorded_long_function_may_shrink_but_not_grow(tmp_path):
    files, functions = _tree(tmp_path, {"routes/c.py": _func("big", 200)})
    assert ratchet.check(files, functions, {"functions": {"routes/c.py::big": 200}}) == []
    assert ratchet.check(files, functions, {"functions": {"routes/c.py::big": 199}})
    assert ratchet.shrunk(files, functions, {"functions": {"routes/c.py::big": 250}}) == ["routes/c.py::big"]


def test_methods_and_nested_functions_have_qualified_names(tmp_path):
    text = "class Calc:\n" + _func("run", 160, indent="    ") + "def outer():\n" + _func("inner", 155, indent="    ")
    _files, functions = _tree(tmp_path, {"calculations/d.py": text})
    assert functions["calculations/d.py::Calc.run"] == 160
    assert functions["calculations/d.py::outer.inner"] == 155


def test_a_big_file_may_not_grow_and_a_new_big_file_fails(tmp_path):
    text = "".join(_func(f"f{i}", 9) for i in range(90))  # 810 lines of short functions
    files, functions = _tree(tmp_path, {"routes/e.py": text, "background_processor.py": "x = 1\n"})
    assert files["routes/e.py"] == 810 and "background_processor.py" in files
    assert ratchet.check(files, functions, {"files": {}}) == ["routes/e.py: file has 810 lines (limit 800)"]
    assert ratchet.check(files, functions, {"files": {"routes/e.py": 810}}) == []
    assert ratchet.check(files, functions, {"files": {"routes/e.py": 805}})


def test_over_limits_records_only_what_is_over_a_limit(tmp_path):
    files, functions = _tree(tmp_path, {"routes/f.py": _func("short", 10) + _func("long", 151)})
    assert ratchet.over_limits(files, functions) == ({}, {"routes/f.py::long": 151})
