# API reference

Everything below is importable from `lowmq_client`.

## LowMqClient

```python
LowMqClient(
    auth_key: str,
    lowmq_url: str | pydantic.AnyUrl,
    *,
    session: aiohttp.ClientSession | None = None,
    timeout: aiohttp.ClientTimeout | None = None,
)
```

- `auth_key` is sent as `Authorization: token <auth_key>` on every request.
- `lowmq_url` must be an `http` or `https` URL. It is validated with pydantic and stored in
  normalized form, for example `https://lowmq.example` becomes `https://lowmq.example/`. Requests go
  to `<lowmq_url>/msg` without a doubled slash. An invalid URL raises `InvalidUrlError`.
- `session` and `timeout` are keyword-only.
- `timeout` applies only to the session the client creates itself. Default:
  `aiohttp.ClientTimeout(total=30)`.

### Session lifecycle

Use the client as an async context manager:

```python
async with LowMqClient(auth_key, url) as client:
    ...
```

Without `session=`, entering the block creates an `aiohttp.ClientSession` and leaving it closes
that session.

With `session=`, the client uses that session and never closes it. You own its lifecycle:

```python
async with aiohttp.ClientSession() as session:
    client = LowMqClient(auth_key, url, session=session)
    await client.add_packet("jobs", {"id": 1})
```

Calling a method with no session, or with a closed one, raises `ClientClosedError`.

### Methods

| Method | HTTP request | Returns |
| --- | --- | --- |
| `await add_packet(queue_name, payload, freeze_time_min=5)` | `POST /msg?freezeTimeMin=<n>` with JSON body `{"key": queue_name, "value": payload}` | parsed response body |
| `await get_packet(queue_name, delete=False)` | `GET /msg?key=<queue_name>&delete=true\|false` | parsed response body |
| `await delete_packet(queue_name, packet_id)` | `DELETE /msg?key=<queue_name>&_id=<packet_id>` | `True` on 2xx, `False` otherwise |
| `await set_auth_key(auth_key)` | none | `None` |
| `await set_lowmq_url(lowmq_url)` | none, validates the URL | `None` |

`add_packet` and `get_packet` raise `ApiError` on a non-2xx response. A 2xx body that is not
valid JSON, including an empty body, is returned as `{"raw": "<text>"}`.

Query parameters are URL encoded, so queue names and ids may contain any characters.

## Exceptions

| Exception | Raised when | Attributes |
| --- | --- | --- |
| `LowMqError` | base class of the exceptions below | |
| `InvalidUrlError` | the server URL is not a valid URL | `url` |
| `ClientClosedError` | a request is made without an open session | |
| `ApiError` | `add_packet` or `get_packet` gets a non-2xx response | `status`, `reason`, `body` |

`ApiError.body` is the parsed JSON body, the response text if the body is not JSON, or `None` if
the body is empty.
