# lowmq-client

[![CI](https://github.com/AI-Stratov/lowmq-python-client/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-Stratov/lowmq-python-client/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/lowmq-client)](https://pypi.org/project/lowmq-client/)

An asyncio client for the [LowMQ](https://github.com/farawayCC/lowmq) message queue, for Python
applications that need to put messages into a LowMQ queue and take them out.

## Install

```bash
pip install lowmq-client
```

## Example

```python
import asyncio

from lowmq_client import LowMqClient


async def main() -> None:
    async with LowMqClient("your-auth-key", "https://lowmq.example.com") as client:
        await client.add_packet("payments", {"amount": 100})
        message = await client.get_packet("payments", delete=True)
        print(message)


asyncio.run(main())
```

## Features

- `add_packet`, `get_packet` and `delete_packet` for the LowMQ `/msg` endpoint.
- `async with` opens and closes an `aiohttp.ClientSession`, with a 30 second total timeout by
  default. Pass `timeout=` to change it.
- Pass your own `session=` to reuse an existing `aiohttp.ClientSession`. The client does not close
  it.
- A non-2xx response from `add_packet` or `get_packet` raises `ApiError` with `status`, `reason`
  and `body`.
- A response body that is not JSON is returned as `{"raw": "<text>"}`.
- The server URL is validated when the client is created; an invalid URL raises `InvalidUrlError`.
- Type hints and a `py.typed` marker; the package is checked with mypy in CI.

The full API is in [docs/api.md](docs/api.md).

## Limitations and compatibility

- Python 3.9 to 3.13. CI runs the tests on each of these versions.
- LowMQ server: no server version is pinned. The client uses the `/msg` HTTP endpoint and sends
  `Authorization: token <key>`. CI does not run against a live server; the tests mock
  `aiohttp`.
- Queue names and message ids are put into the query string without URL encoding. Avoid `&`,
  `?`, `#` and spaces in them.
- `delete_packet` returns `False` on a non-2xx response instead of raising.
- No retries or batching.

## Development

```bash
uv sync
uv run python -m unittest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

`pre-commit install` sets up the same checks as git hooks.

Releases: bump `version` in `pyproject.toml`, then push a tag `v<version>`. CI publishes the
package to PyPI after lint and tests pass.

## License

MIT, see [LICENSE](LICENSE).
