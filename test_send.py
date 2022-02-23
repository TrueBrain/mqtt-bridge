import asyncio
import json
import time

from asyncio_mqtt import Client


async def main():
    async with Client("localhost") as client:
        remote = {
            "remote": "127.0.0.1:1900",
            "on_initialize": json.dumps({"state": "init"}),
            "on_disconnect": json.dumps({"state": "error"}),
        }
        await client.publish("category/data/remote", payload=json.dumps(remote))

    await asyncio.sleep(1)

    for _ in range(10):
        async with Client("localhost", 1900) as client:
            data = {
                "state": "valid",
                "payload": time.time(),
            }
            await client.publish("category/data", payload=json.dumps(data))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
