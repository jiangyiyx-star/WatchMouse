"""Loopback transport comparison; all desktop input is mocked.

Run: py -3 tests/benchmark_receiver.py --requests 1000 --rounds 3
This measures HTTP transport on this computer, not phone/Wi-Fi latency.
"""
from __future__ import annotations

import argparse
import http.client
import json
from pathlib import Path
import statistics
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from input_control import InputController
import receiver


def run(requests, protocol, buffered, no_delay):
    class BenchmarkHandler(receiver.Handler):
        protocol_version = protocol
        wbufsize = 65536 if buffered else 0
        disable_nagle_algorithm = no_delay

    class BenchmarkServer(receiver.ReceiverServer):
        accepted_connections = 0

        def process_request(self, request, client_address):
            self.accepted_connections += 1
            super().process_request(request, client_address)

    server = BenchmarkServer(("127.0.0.1", 0), "benchmark-token",
                             InputController(sender=lambda items: None))
    server.RequestHandlerClass = BenchmarkHandler
    worker = threading.Thread(target=server.serve_forever,
                              kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    body = json.dumps({"command": "M 2,1"})
    headers = {"Content-Type": "application/json", "X-WatchMouse-Token": "benchmark-token"}
    samples = []
    try:
        for _ in range(20):
            connection.request("POST", "/api/command", body, headers)
            response = connection.getresponse()
            if response.status != 200 or not json.loads(response.read())["ok"]:
                raise RuntimeError("Benchmark warm-up failed")
        connection.close()
        server.accepted_connections = 0
        started = time.perf_counter()
        cpu_started = time.process_time()
        for _ in range(requests):
            before = time.perf_counter()
            connection.request("POST", "/api/command", body, headers)
            response = connection.getresponse()
            if response.status != 200 or not json.loads(response.read())["ok"]:
                raise RuntimeError("Benchmark command failed")
            samples.append((time.perf_counter() - before) * 1000)
        cpu_seconds = time.process_time() - cpu_started
        seconds = time.perf_counter() - started
        samples.sort()
        return {"transport": protocol, "requests": requests,
                "connections_and_handler_threads": server.accepted_connections,
                "seconds": round(seconds, 3), "cpu_seconds": round(cpu_seconds, 3),
                "requests_per_second": round(requests / seconds, 1),
                "p50_ms": round(statistics.median(samples), 3),
                "p95_ms": round(samples[min(len(samples) - 1, int(len(samples) * .95))], 3)}
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    if args.requests <= 0 or args.rounds <= 0:
        parser.error("requests and rounds must be positive")
    for round_index in range(args.rounds):
        for protocol, buffered, no_delay in (("HTTP/1.0", False, False), ("HTTP/1.1", True, True)):
            result = run(args.requests, protocol, buffered, no_delay)
            print(json.dumps({"round": round_index + 1, **result}))


if __name__ == "__main__":
    main()
