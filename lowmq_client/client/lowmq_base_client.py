import aiohttp
from pydantic import AnyUrl


class LowMqBaseClient:
    def __init__(self, auth_key: str, lowmq_url: AnyUrl):
        self.auth_key = auth_key
        self.lowmq_url = lowmq_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    async def set_auth_key(self, auth_key):
        self.auth_key = auth_key

    async def set_lowmq_url(self, lowmq_url):
        self.lowmq_url = lowmq_url

    async def add_packet(self, queue_name, payload, freeze_time_min=5):
        url = f"{self.lowmq_url}/msg?freezeTimeMin={freeze_time_min}"
        headers = {
            "Authorization": f"token {self.auth_key}",
            "Content-Type": "application/json",
        }
        data = {"key": queue_name, "value": payload}

        async with self.session.post(url, headers=headers, json=data) as response:
            response_data = await response.json()
            return response_data

    async def get_packet(self, queue_name, delete=False):
        url = f"{self.lowmq_url}/msg?key={queue_name}&delete={str(delete).lower()}"
        headers = {"Authorization": f"token {self.auth_key}"}

        async with self.session.get(url, headers=headers) as response:
            response_data = await response.json()
            return response_data

    async def delete_packet(self, queue_name, packet_id):
        url = f"{self.lowmq_url}/msg?key={queue_name}&_id={packet_id}"
        headers = {"Authorization": f"token {self.auth_key}"}

        async with self.session.delete(url, headers=headers) as response:
            if response.status == 200:
                return True
            else:
                return False
