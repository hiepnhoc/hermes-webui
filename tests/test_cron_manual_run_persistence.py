"""Regression tests for manual WebUI cron runs."""

from contextlib import contextmanager
from datetime import datetime, timezone


def _install_cron_fakes(monkeypatch, calls, deliver_result=None, silent_marker="[SILENT]"):
    cron_jobs = type("CronJobs", (), {})()
    cron_jobs.save_job_output = lambda job_id, output: calls.append(
        ("save", job_id, output)
    )
    cron_jobs.mark_job_run = lambda job_id, success, error=None, delivery_error=None: calls.append(
        ("mark", job_id, success, error, delivery_error)
    )

    cron_scheduler = type("CronScheduler", (), {})()
    cron_scheduler.SILENT_MARKER = silent_marker
    if deliver_result is None:
        deliver_result = lambda job, content: calls.append(
            ("deliver", job["id"], content)
        ) or None
    cron_scheduler._deliver_result = deliver_result

    monkeypatch.setitem(__import__("sys").modules, "cron.jobs", cron_jobs)
    monkeypatch.setitem(__import__("sys").modules, "cron.scheduler", cron_scheduler)


def test_manual_cron_run_saves_output_delivers_and_marks_job(monkeypatch):
    import api.routes as routes

    calls = []
    _install_cron_fakes(monkeypatch, calls)
    monkeypatch.setattr(
        routes,
        "_run_cron_job_in_profile_subprocess",
        lambda job, execution_profile_home: (True, "manual output", "done", None),
    )

    routes._mark_cron_running("job123")
    routes._run_cron_tracked({"id": "job123"})

    assert calls == [
        ("save", "job123", "manual output"),
        ("deliver", "job123", "done"),
        ("mark", "job123", True, None, None),
    ]
    assert routes._is_cron_running("job123") == (False, 0.0)


def test_manual_cron_run_marks_empty_response_as_failure_without_delivery(monkeypatch):
    import api.routes as routes

    calls = []
    _install_cron_fakes(monkeypatch, calls)
    monkeypatch.setattr(
        routes,
        "_run_cron_job_in_profile_subprocess",
        lambda job, execution_profile_home: (True, "manual output", "", None),
    )

    routes._mark_cron_running("job-empty")
    routes._run_cron_tracked({"id": "job-empty"})

    assert calls[0] == ("save", "job-empty", "manual output")
    assert calls[1][0:3] == ("mark", "job-empty", False)
    assert "empty response" in calls[1][3]
    assert calls[1][4] is None
    assert routes._is_cron_running("job-empty") == (False, 0.0)


def test_manual_cron_run_records_delivery_errors_separately(monkeypatch):
    import api.routes as routes

    calls = []

    def fail_delivery(job, content):
        calls.append(("deliver", job["id"], content))
        return "discord not configured"

    _install_cron_fakes(monkeypatch, calls, deliver_result=fail_delivery)
    monkeypatch.setattr(
        routes,
        "_run_cron_job_in_profile_subprocess",
        lambda job, execution_profile_home: (True, "manual output", "done", None),
    )

    routes._mark_cron_running("job-delivery-error")
    routes._run_cron_tracked({"id": "job-delivery-error"})

    assert calls == [
        ("save", "job-delivery-error", "manual output"),
        ("deliver", "job-delivery-error", "done"),
        ("mark", "job-delivery-error", True, None, "discord not configured"),
    ]
    assert routes._is_cron_running("job-delivery-error") == (False, 0.0)


def test_manual_cron_run_skips_silent_success_delivery(monkeypatch):
    import api.routes as routes

    calls = []
    _install_cron_fakes(monkeypatch, calls)
    monkeypatch.setattr(
        routes,
        "_run_cron_job_in_profile_subprocess",
        lambda job, execution_profile_home: (True, "manual output", "[SILENT]", None),
    )

    routes._mark_cron_running("job-silent")
    routes._run_cron_tracked({"id": "job-silent"})

    assert calls == [
        ("save", "job-silent", "manual output"),
        ("mark", "job-silent", True, None, None),
    ]
    assert routes._is_cron_running("job-silent") == (False, 0.0)


def test_manual_cron_run_delivers_failure_notice(monkeypatch):
    import api.routes as routes

    calls = []
    _install_cron_fakes(monkeypatch, calls)
    monkeypatch.setattr(
        routes,
        "_run_cron_job_in_profile_subprocess",
        lambda job, execution_profile_home: (False, "manual output", "", "boom"),
    )

    routes._mark_cron_running("job-failed")
    routes._run_cron_tracked({"id": "job-failed", "name": "Nightly check"})

    assert calls[0] == ("save", "job-failed", "manual output")
    assert calls[1][0:2] == ("deliver", "job-failed")
    assert "Nightly check" in calls[1][2]
    assert "boom" in calls[1][2]
    assert calls[2] == ("mark", "job-failed", False, "boom", None)
    assert routes._is_cron_running("job-failed") == (False, 0.0)


def test_manual_cron_run_records_status_without_advancing_schedule(monkeypatch):
    import api.routes as routes

    original = {
        "id": "job-stable-schedule",
        "next_run_at": "2026-07-14T15:00:00+07:00",
        "repeat": {"times": None, "completed": 8},
        "enabled": True,
        "state": "scheduled",
        "schedule": {"kind": "cron", "expr": "0 15 * * *"},
    }
    stored = [original.copy()]

    @contextmanager
    def jobs_lock():
        yield

    cron_jobs = type("CronJobs", (), {})()
    cron_jobs._jobs_lock = jobs_lock
    cron_jobs.load_jobs = lambda: stored
    cron_jobs.save_jobs = lambda jobs: stored.__setitem__(slice(None), jobs)
    cron_jobs._hermes_now = lambda: datetime(2026, 7, 13, 11, 30, tzinfo=timezone.utc)
    cron_jobs.mark_job_run = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("manual runs must not call mark_job_run when metadata-safe storage is available")
    )
    monkeypatch.setitem(__import__("sys").modules, "cron.jobs", cron_jobs)

    routes._record_manual_cron_run(
        "job-stable-schedule", True, None, delivery_error=None
    )

    saved = stored[0]
    assert saved["next_run_at"] == original["next_run_at"]
    assert saved["repeat"] == original["repeat"]
    assert saved["enabled"] is True
    assert saved["state"] == "scheduled"
    assert saved["last_status"] == "ok"
    assert saved["last_run_at"] == "2026-07-13T11:30:00+00:00"
