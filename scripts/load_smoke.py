#!/usr/bin/env python3
"""Lightweight load smoke test for a single endpoint."""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import httpx


async def _worker(
    queue: asyncio.Queue[object],
    client: httpx.AsyncClient,
    url: str,
    timeout: float,
    latencies: list[float],
    errors: list[str],
) -> None:
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            return

        start = time.perf_counter()
        try:
            resp = await client.get(url, timeout=timeout)
            resp.raise_for_status()
            latencies.append(time.perf_counter() - start)
        except Exception as exc:  # pragma: no cover - exercised in failures
            errors.append(str(exc))
        finally:
            queue.task_done()


async def _run(url: str, total: int, concurrency: int, timeout: float) -> int:
    queue: asyncio.Queue[object] = asyncio.Queue()
    for _ in range(total):
        queue.put_nowait(object())
    for _ in range(concurrency):
        queue.put_nowait(None)

    latencies: list[float] = []
    errors: list[str] = []

    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(
                _worker(queue, client, url, timeout, latencies, errors)
            )
            for _ in range(concurrency)
        ]
        started = time.perf_counter()
        await queue.join()
        for task in tasks:
            await task
        duration = time.perf_counter() - started

    if errors:
        preview = "\n".join(errors[:5])
        print(f"load failed: {len(errors)} errors\n{preview}")
        return 1

    if not latencies:
        print("load failed: no successful responses recorded")
        return 1

    lat_ms = sorted(lat * 1000 for lat in latencies)
    p50 = statistics.median(lat_ms)
    p95_index = max(int(len(lat_ms) * 0.95) - 1, 0)
    p95 = lat_ms[p95_index]
    rps = total / duration if duration else 0.0
    print(
        "load ok "
        f"total={total} concurrency={concurrency} duration_s={duration:.2f} "
        f"rps={rps:.1f} p50_ms={p50:.1f} p95_ms={p95:.1f}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Load smoke test for an endpoint.")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/health",
        help="Target URL for the smoke test.",
    )
    parser.add_argument("--total", type=int, default=200, help="Total requests.")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrency.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds.")
    args = parser.parse_args()

    if args.total < 1:
        print("total must be >= 1")
        return 2
    if args.concurrency < 1:
        print("concurrency must be >= 1")
        return 2
    concurrency = min(args.concurrency, args.total)

    return asyncio.run(_run(args.url, args.total, concurrency, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
