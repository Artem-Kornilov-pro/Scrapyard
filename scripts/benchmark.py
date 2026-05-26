"""Simple benchmark script for the Scrapyard API."""

import time

import requests

BASE_URL = "http://localhost:8000"

VALID_JOB = {
    "name": "Benchmark Job",
    "url": "https://example.com",
    "selectors": {
        "items": "div.product",
        "fields": {
            "title": {"selector": "h3", "attr": "text", "type": "string"},
        },
    },
}


def run_benchmark(num_jobs: int = 100) -> None:
    """Create jobs and measure response times."""
    print(f"Creating {num_jobs} jobs...")
    times: list[float] = []

    for i in range(num_jobs):
        start = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/jobs",
                json=VALID_JOB,
                timeout=5,
            )
            elapsed = time.time() - start
            times.append(elapsed)

            if response.status_code == 201:
                print(f"  Job {i + 1}: {elapsed:.3f}s")
            else:
                print(f"  Job {i + 1}: FAILED ({response.status_code})")

        except requests.RequestException as e:
            print(f"  Job {i + 1}: ERROR ({e})")

    if times:
        avg = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        print(f"\nResults for {len(times)} successful requests:")
        print(f"  Average: {avg:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")


if __name__ == "__main__":
    run_benchmark(100)
