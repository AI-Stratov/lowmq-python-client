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

- `add_packet`, `get_packet` and `delete_packet` for the LowMQ `/msg` endpoint. Queue names and
  message ids are URL encoded.
- `async with` opens and closes an `aiohttp.ClientSession`, with a 30 second total timeout by
  default. Pass `timeout=` to change it.
- Pass your own `session=` to reuse an existing `aiohttp.ClientSession`. The client does not close
  it.
- A non-2xx response from `add_packet` or `get_packet` raises `ApiError` with `status`, `reason`
  and `body`.
- A response body that is not JSON is returned as `{"raw": "<text>"}`.
- The server URL is validated when the client is created. Only `http` and `https` URLs are
  accepted; anything else raises `InvalidUrlError`.
- Type hints and a `py.typed` marker. CI runs mypy in strict mode.

The full API is in [docs/api.md](docs/api.md).

## Limitations and compatibility

- Python 3.10 to 3.14. CI runs the tests on each of these versions, and once more on Python 3.10
  with the oldest allowed `aiohttp` (3.10.11) and `pydantic` (2.10).
- LowMQ server: no server version is pinned. The client uses the `/msg` HTTP endpoint and sends
  `Authorization: token <key>`. The tests run against an in-process fake server, not a real
  LowMQ.
- `delete_packet` returns `False` on a non-2xx response instead of raising.
- No retries or batching.

## Development

```bash
uv sync
uv run coverage run -m unittest -v
uv run coverage report
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

The tests need no running services. Coverage must stay at 100 percent. `uv run pre-commit install`
runs ruff and mypy as git hooks, using the versions from `uv.lock`.

Releases: bump `version` in `pyproject.toml`, then push a tag `v<version>`. After lint and tests
pass, CI publishes the package to PyPI and creates a GitHub release with generated notes.

## License

MIT, see [LICENSE](LICENSE).
