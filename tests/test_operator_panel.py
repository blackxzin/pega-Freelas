from pathlib import Path

import pytest

from freelahunter.operator_panel import (
    HunterProcessManager,
    hunter_command,
    hunter_environment,
    load_platforms,
)


ROOT = Path(__file__).resolve().parents[1]


def test_platform_defaults_keep_99freelas_and_upwork_separate():
    platforms = load_platforms(ROOT / "config" / "platforms.json")

    assert platforms["99freelas"].max_jobs == 5
    assert platforms["99freelas"].interval_minutes == 15
    assert platforms["upwork"].max_jobs == 2
    assert platforms["upwork"].interval_minutes == 12
    assert platforms["upwork"].locale == "en-US"
    assert platforms["upwork"].currency == "USD"


def test_hunter_environment_always_starts_in_safe_draft_mode():
    platform = load_platforms(ROOT / "config" / "platforms.json")["upwork"]
    env = hunter_environment(platform, {"PATH": "/usr/bin", "AUTO_SEND": "true"})

    assert env["PLATFORM"] == "upwork"
    assert env["MAX_JOBS"] == "2"
    assert env["HUNT_INTERVAL_MINUTES"] == "12"
    assert env["AUTO_SEND"] == "false"
    assert env["DRY_RUN"] == "true"
    assert env["AUTOMATION_MODE"] == "SEMI_AUTO"


def test_hunter_command_does_not_use_shell():
    command = hunter_command(ROOT)
    assert command == ["node", str(ROOT / "scripts" / "interactive_hunt.mjs")]


def test_manager_rejects_unknown_platform_without_starting():
    manager = HunterProcessManager(ROOT)
    with pytest.raises(ValueError):
        manager.start("linkedin")
