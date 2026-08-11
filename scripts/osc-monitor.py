"""Print incoming OSC messages while Max or TouchDesigner is not running."""

import argparse

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer


def print_message(address, *values):
    print(address, *values, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(print_message)
    server = BlockingOSCUDPServer((args.host, args.port), dispatcher)
    print(f"Listening for OSC on {args.host}:{args.port} (Ctrl+C to stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
