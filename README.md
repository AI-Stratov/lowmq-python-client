# LowMQ Python Client

[![PyPI version](https://img.shields.io/pypi/v/lowmq-client?color=black&style=for-the-badge)](https://pypi.org/project/lowmq-client/)
[![Python versions](https://img.shields.io/pypi/pyversions/lowmq-client?style=for-the-badge)](https://pypi.org/project/lowmq-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg?style=for-the-badge)](./LICENSE)

An ergonomic, type-annotated, asyncio-based client for LowMQ — a lightweight message queue.

- LowMQ server repo: https://github.com/farawayCC/lowmq
- This package: https://pypi.org/project/lowmq-client/

## Highlights

- Async-first API built on top of aiohttp
- Fully type-annotated, ships py.typed for type checkers
- Safe JSON handling and helpful exceptions
- Pluggable aiohttp session and configurable timeouts
- Tiny footprint, minimal required deps

## Install

Using pip:

```bash
pip install lowmq-client
```

For development (linters, tests, etc.):

```bash
pip install -e .[dev]
pre-commit install
```

Using uv (fast Python package manager):

```bash
# Install uv with pipx (recommended)
pipx install uv

# Sync the project (installs core + dev, as configured)
uv sync

# Activate the virtual environment that uv manages
# Windows PowerShell:
. .venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pre-commit install
```

## Quickstart

```python
import asyncio
from lowmq_client import LowMqClient

async def main() -> None:
    base_url = "https://your-lowmq-server.com"
    auth_key = "your-auth-key"

    async with LowMqClient(auth_key, base_url) as client:
        # Add a message to a queue
        add_res = await client.add_packet("payments", {"amount": 100}, freeze_time_min=5)
        print("added:", add_res)

        # Get a message from a queue (and keep it in the queue)
        msg = await client.get_packet("payments", delete=False)
        print("fetched:", msg)

        # Delete a message by id
        if msg and "_id" in msg:
            ok = await client.delete_packet("payments", msg["_id"])
            print("deleted:", ok)

asyncio.run(main())
```

## API

- LowMqClient(auth_key: str, lowmq_url: str | pydantic.AnyUrl, session: Optional[aiohttp.ClientSession] = None, timeout: Optional[aiohttp.ClientTimeout] = None)
  - Asynchronous client. Can re-use an external aiohttp session.
- await set_auth_key(auth_key: str) -> None
- await set_lowmq_url(lowmq_url: str | pydantic.AnyUrl) -> None
- await add_packet(queue_name: str, payload: Any, freeze_time_min: int = 5) -> dict
  - POST /msg?freezeTimeMin=...
- await get_packet(queue_name: str, delete: bool = False) -> dict
  - GET /msg?key=...&delete=true|false
- await delete_packet(queue_name: str, packet_id: str) -> bool
  - DELETE /msg?key=...&_id=...

### Exceptions

- LowMqError — base class for client exceptions
- InvalidUrlError — invalid LowMQ base URL
- ClientClosedError — client used without an active session
- ApiError — server returned non-2xx, includes status, reason, and parsed body when possible

## Typing

This package is fully typed and includes a py.typed marker. You can rely on type
checkers (mypy/pyright) to validate your usage. The public API returns standard
Python types (dict) for server responses; you can define your own Pydantic
models if you prefer stronger typing for message payloads.

## Recipes

- Reusing your aiohttp session:

```python
import aiohttp
from lowmq_client import LowMqClient

session = aiohttp.ClientSession()
client = LowMqClient("key", "https://lowmq.example", session=session)
# ... use client inside an async context as usual ...
```

- Custom timeout:

```python
import aiohttp
from lowmq_client import LowMqClient

client = LowMqClient(
    "key",
    "https://lowmq.example",
    timeout=aiohttp.ClientTimeout(total=10),
)
```

## Development

- Lint and format (Ruff):

```bash
ruff check .
ruff format .
```

- Tests:

```bash
python -m unittest -v
```

- Pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

## Links

- LowMQ server: https://github.com/farawayCC/lowmq
- PyPI: https://pypi.org/project/lowmq-client/
- Issues: https://github.com/AI-Stratov/lowmq-python-client/issues

## License

MIT
