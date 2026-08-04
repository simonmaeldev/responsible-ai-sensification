"""Tests for the model-free Ubuntu-to-receiver OSC fixture."""

import threading

import pytest
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

from scripts.send_osc_test import _parser, _token_event, main


def test_lan_fixture_requires_explicit_destination():
    with pytest.raises(SystemExit):
        _parser().parse_args([])


def test_lan_fixture_contains_final_post_tonality_sentinel():
    event = _token_event(7, "fixture", 11)

    sentinel = next(
        note for note in event["notes"]
        if note["feature_index"] == 54321
    )

    assert sentinel["freq"] == 445.125
    assert sentinel["raw_freq"] == 440.0
    assert sentinel["amplitude"] == 0.90
    assert event["tonality"]["matches"][0]["name"] == "ubuntu lan fixture"


def test_lan_fixture_sends_complete_contract_to_real_loopback_receiver():
    received = []
    stopped = threading.Event()

    def capture(address, *args):
        received.append((address, args))
        if address == "/rai/v1/run/stop":
            stopped.set()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(capture)
    server = BlockingOSCUDPServer(("127.0.0.1", 0), dispatcher)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        exit_code = main([
            "--host",
            "127.0.0.1",
            "--port",
            str(server.server_address[1]),
            "--max-notes",
            "2",
            "--delay-ms",
            "0",
        ])
        assert exit_code == 0
        assert stopped.wait(2), "loopback receiver did not receive /run/stop"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    addresses = [address for address, _ in received]
    assert addresses[0] == "/rai/v1/run/start"
    assert addresses[-3:] == [
        "/rai/v1/run/done",
        "/rai/v1/run/silent",
        "/rai/v1/run/stop",
    ]
    assert addresses.count("/rai/v1/token") == 2
    assert addresses.count("/rai/v1/note") == 4
    assert addresses.count("/rai/v1/token/end") == 2
    assert addresses.count("/rai/v1/control/bpm") == 2

    frequencies = [
        round(args[4], 3)
        for address, args in received
        if address == "/rai/v1/note"
    ]
    assert frequencies == [445.125, 333.75, 445.125, 333.75]
