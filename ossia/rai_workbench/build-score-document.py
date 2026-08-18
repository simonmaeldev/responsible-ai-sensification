"""Generate rai-workbench.score through installed ossia score."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time


PROTOCOL_UUID = "59e81303-af24-4559-b33d-1c6f59f0f017"
WEBSOCKET_URL = "ws://127.0.0.1:8080/ws/stream"
RESULT_MARKER = "RAI_SCORE_DOCUMENT_CREATED"


def generator_qml(device_qml: Path, output: Path) -> str:
    """Return a temporary score UI that creates and saves the device document."""
    device_path = json.dumps(str(device_qml.resolve()))
    output_path = json.dumps(str(output.resolve()))
    return f'''import QtQuick
import Score.UI as UI

Rectangle {{
  width: 32
  height: 32

  Component.onCompleted: {{
    console.log("RAI_SCORE_DOCUMENT_GENERATOR_STARTED");
    Score.removeDevice("RAI Workbench");
    createDevice.start();
  }}

  Timer {{
    id: createDevice
    interval: 500
    repeat: false
    onTriggered: {{
      var deviceCode = Score.readFile({device_path});
      if (deviceCode.length === 0) {{
        console.error("RAI_SCORE_DOCUMENT_ERROR empty device QML");
        return;
      }}
      Score.createDevice(
        "RAI Workbench",
        "{PROTOCOL_UUID}",
        {{
          Address: "{WEBSOCKET_URL}",
          Text: deviceCode,
        }}
      );
      console.log("RAI_SCORE_DOCUMENT_DEVICE_CREATED");
      saveDocument.start();
    }}
  }}

  Timer {{
    id: saveDocument
    interval: 1000
    repeat: false
    onTriggered: {{
      Score.save();
      console.log("{RESULT_MARKER} " + {output_path});
    }}
  }}
}}
'''


def build(score_binary: str, device_qml: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.is_file():
        raise FileNotFoundError(
            f"Restore the committed score-generated seed document before rebuilding: "
            f"{output}"
        )
    with tempfile.TemporaryDirectory(prefix="rai-score-document-") as path:
        generator = Path(path) / "create-score-document.qml"
        generator.write_text(
            generator_qml(device_qml, output),
            encoding="utf8",
        )

        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "offscreen"
        command = [
            score_binary,
            "--no-restore",
            "--no-opengl",
            "--ui-debug",
            str(generator),
        ]
        command.append(str(output.resolve()))
        process = subprocess.Popen(
            command,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        output_bytes = bytearray()
        deadline = time.monotonic() + 30
        try:
            while time.monotonic() < deadline:
                if process.stdout is None:
                    break
                readable, _, _ = select.select(
                    [process.stdout],
                    [],
                    [],
                    max(0, min(0.5, deadline - time.monotonic())),
                )
                if readable:
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    output_bytes.extend(chunk)
                    if RESULT_MARKER.encode() in output_bytes:
                        break
                elif process.poll() is not None:
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stdout is not None:
                output_bytes.extend(process.stdout.read())

    output_text = output_bytes.decode(errors="replace")
    if RESULT_MARKER not in output_text:
        raise RuntimeError(
            "ossia score did not report a saved document\n" + output_text[-8000:]
        )
    if not output.is_file():
        raise RuntimeError(f"ossia score did not create {output}")
    print(f"{RESULT_MARKER} {output}")


def main() -> None:
    workbench = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-binary", default="ossia-score")
    parser.add_argument(
        "--device-qml",
        type=Path,
        default=workbench / "websocket-device.qml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=workbench / "rai-workbench.score",
    )
    args = parser.parse_args()
    build(args.score_binary, args.device_qml, args.output)


if __name__ == "__main__":
    main()
