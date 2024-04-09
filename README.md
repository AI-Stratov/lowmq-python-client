# Python client for LowMQ

This is a Python asynchronous client for interacting with LowMQ, a message queuing service. The client allows you to
send, retrieve, and delete messages from queues hosted on a LowMQ server.

[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/farawayCC/lowmq)

## Usage

Here's a quick guide on how to use the LowMQ client:

```
from lowmq_client import LowMqClient

async def main():
    # Initialize the LowMQ client
    lowmq_url = "https://your-lowmq-server.com"
    auth_key = "your-auth-key"
    async with LowMqClient(auth_key, lowmq_url) as client:
        # Add a packet to a queue
        await client.add_packet("queue_name", {"key": "value"})

        # Get a packet from a queue
        packet = await client.get_packet("queue_name")
        print(packet)

        # Delete a packet from a queue
        packet_id = packet['_id']
        await client.delete_packet("queue_name", packet_id)

```

## API Reference

* **`LowMqClient(auth_key: str, lowmq_url: str)`**
  Constructor for the LowMQ client.
  * `auth_key:` Authentication key for accessing the LowMQ server.
  * `lowmq_url:` URL of the LowMQ server.

* **`async set_auth_key(auth_key: str)`**
  Set a new authentication key.
  * `auth_key:` New authentication key.

* **`async set_lowmq_url(lowmq_url: str)`**
  Set a new LowMQ server URL.
  * `lowmq_url:` New LowMQ server URL.

* **`async add_packet(queue_name: str, payload: dict, freeze_time_min: int = 5) -> dict`**
  Add a packet to a queue.
  * `queue_name:` Name of the queue.
  * `payload:` Payload of the packet.
  * `freeze_time_min:` Optional. Freeze time for the message in minutes (default is 5).

* **`async get_packet(queue_name: str, delete: bool = False) -> dict`**
  Retrieve a packet from a queue.
  * `queue_name:` Name of the queue.
  * `delete:` Optional. If True, the retrieved packet will be deleted from the queue (default is False).

* **`async delete_packet(queue_name: str, packet_id: str) -> bool`**
  Delete a packet from a queue.
  * `queue_name:` Name of the queue.
  * `packet_id:` ID of the packet to delete.
