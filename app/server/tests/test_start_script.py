"""Behavior checks for the Ubuntu Emitter launcher."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time


REPO_ROOT = Path(__file__).resolve().parents[3]
START_SCRIPT = REPO_ROOT / "scripts" / "start.sh"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def _run_launcher(tmp_path: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    command_dir = tmp_path / "bin"
    command_dir.mkdir()
    browser_log = tmp_path / "browser.log"
    uv_log = tmp_path / "uv.log"
    _write_executable(
        command_dir / "curl",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        command_dir / "xdg-open",
        '#!/usr/bin/env bash\nprintf "%s\\n" "$1" > "$BROWSER_LAUNCH_LOG"\n',
    )
    _write_executable(
        command_dir / "uv",
        '#!/usr/bin/env bash\nprintf "%s\\n" "$*" > "$UV_LAUNCH_LOG"\nsleep 0.1\n',
    )
    environment = {
        **os.environ,
        "PATH": f"{command_dir}:{os.environ['PATH']}",
        "DISPLAY": ":test",
        "BROWSER_LAUNCH_LOG": str(browser_log),
        "UV_LAUNCH_LOG": str(uv_log),
    }
    result = subprocess.run(
        ["bash", str(START_SCRIPT), *arguments],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    return result, browser_log, uv_log


def test_start_opens_emitter_in_default_browser(tmp_path: Path) -> None:
    result, browser_log, uv_log = _run_launcher(tmp_path)

    for _attempt in range(50):
        if browser_log.exists():
            break
        time.sleep(0.01)

    assert result.returncode == 0
    assert browser_log.read_text(encoding="utf-8").strip() == "http://127.0.0.1:8080"
    assert "run uvicorn app.server.main:app" in uv_log.read_text(encoding="utf-8")


def test_no_browser_flag_starts_server_without_opening_browser(tmp_path: Path) -> None:
    result, browser_log, uv_log = _run_launcher(tmp_path, "--no-browser")

    assert result.returncode == 0
    assert not browser_log.exists()
    assert "run uvicorn app.server.main:app" in uv_log.read_text(encoding="utf-8")

