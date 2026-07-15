# tests for src/render.py's resolve_output_path: pure path logic (no Jinja/model needed).
# The guarantee under test is that every resolved path stays inside render.OUTPUT_DIR, so
# render_html() can never be steered into overwriting a file elsewhere on disk.
import os
from src import render

def test_empty_outfile_uses_default_location():
    assert render.resolve_output_path("") == render.DEFAULT_OUTPUT_FILE # no outfile -> default file in OUTPUT_DIR

def test_relative_path_is_sandboxed_to_basename_in_output_dir():
    # any leading directories on a relative path are stripped; only the filename survives
    result = render.resolve_output_path(os.path.join("some", "nested", "page.html"))
    assert result == os.path.join(render.OUTPUT_DIR, "page.html") # relative path collapses to OUTPUT_DIR/page.html

def test_absolute_path_inside_output_dir_is_respected():
    # an absolute path that already lives under OUTPUT_DIR is returned unchanged
    inside = os.path.join(render.OUTPUT_DIR, "report.html")
    assert render.resolve_output_path(inside) == inside # confined absolute path is kept as-is

def test_absolute_path_outside_output_dir_falls_back_to_basename():
    # an absolute path outside OUTPUT_DIR must NOT be honoured; only its filename is reused
    outside = os.path.join(render.BASE_DIR, "not_output", "evil.html")
    result = render.resolve_output_path(outside)
    assert result == os.path.join(render.OUTPUT_DIR, "evil.html") # escapes are redirected back into OUTPUT_DIR

def test_absolute_path_with_dotdot_escape_is_not_confined():
    # a path that uses ".." to climb out of OUTPUT_DIR is caught by normalisation
    sneaky = os.path.join(render.OUTPUT_DIR, "..", "secret.html")
    result = render.resolve_output_path(sneaky)
    assert result == os.path.join(render.OUTPUT_DIR, "secret.html") # ".." escape is redirected back into OUTPUT_DIR
