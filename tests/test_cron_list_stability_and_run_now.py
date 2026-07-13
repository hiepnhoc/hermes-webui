"""Regression coverage for stable cron sidebar rows and inline manual runs."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_cron_list_reconciles_against_previous_visual_order():
    src = _read("static/panels.js")
    assert "let _cronStableOrderKeys = [];" in src
    assert "function _stabilizeCronJobOrder(jobs)" in src
    assert "_cronStableOrderKeys = ordered.map(_cronJobKey);" in src
    assert "_cronList = _stabilizeCronJobOrder(data.jobs || []);" in src


def test_cron_list_refresh_preserves_scroll_position():
    src = _read("static/panels.js")
    assert "const previousScrollTop = box.scrollTop;" in src
    assert "box.scrollTop = Math.min(previousScrollTop, box.scrollHeight);" in src


def test_each_writable_cron_row_has_inline_run_now_button():
    src = _read("static/panels.js")
    assert 'class="cron-list-run-now"' in src
    assert "runCronNowFromList(event, '${esc(String(job.id))}')" in src
    assert "job.read_only ? ''" in src
    assert "t('cron_run_now')" in src


def test_inline_run_now_stops_row_navigation_and_calls_existing_run_api():
    src = _read("static/panels.js")
    assert "async function runCronNowFromList(event, jobId)" in src
    assert "event.stopPropagation();" in src
    assert "await cronRun(job.id" in src
    assert "button.disabled = true;" in src


def test_inline_run_button_has_stable_layout_css():
    css = _read("static/style.css")
    assert ".cron-list-run-now{" in css
    assert ".cron-header{display:grid;" in css
    assert "grid-template-columns:auto minmax(0,1fr) auto;" in css
    assert ".cron-row-actions{" in css
