import asyncio
import json

from asyncio_mqtt import Client
from dataclasses import dataclass


@dataclass
class Config:
    remote: str
    on_initialize: str
    on_disconnect: str


def decoder(data):
    return Config(
        data["remote"],
        data["on_initialize"],
        data["on_disconnect"],
    )


class Subscriber:
    def __init__(self, remote, publish_queue):
        self._topics = {}
        self._publish_queue = publish_queue

        # XXX -- This demands the port to also be part of the remote, which is a silly requirement.
        ip, _, port = remote.partition(":")
        # Create the client for the remote broker.
        self._client = Client(ip, int(port))

        # On startup, create a asyncio task to connect to the remote broker.
        asyncio.create_task(self.run())

    async def run(self):
        # XXX -- Disconnect events are not handled, but should publish self._config.on_disconnect.

        # Start a connection to the remote broker.
        await self._client.connect()

        # Make sure we are subscribed to all the requested topics.
        for topic in self._topics.keys():
            await self._client.subscribe(topic)

        # Check for any incoming messages.
        async with self._client.unfiltered_messages() as messages:
            async for message in messages:
                # Relay the message to the internal broker.
                self._publish_queue.put_nowait((message.topic, message.payload))

    async def subscribe(self, config, topic):
        if topic in self._topics:
            return
        self._topics[topic] = config

        # Initialize the topic as requested.
        self._publish_queue.put_nowait((topic, config.on_initialize))

        # XXX - Tiny bit racy; should have locks to ensure we don't connect while checking.
        if self._client._connected.done():
            # Subscribe if we are already connected; otherwise run() subscribes for us.
            await self._client.subscribe(topic)


class SubscribeManager:
    def __init__(self, publish_queue):
        self._remotes = {}
        self._publish_queue = publish_queue

    async def configure(self, config, topic):
        # Check if we already have a connection to the remote broker.
        if config.remote not in self._remotes:
            # We do not; create one.
            self._remotes[config.remote] = Subscriber(
                config.remote, self._publish_queue
            )

        # Subscribe on the remote broker to the requested topic.
        await self._remotes[config.remote].subscribe(config, topic)


async def config_sub(mng):
    async with Client("localhost") as client:
        async with client.unfiltered_messages() as messages:
            # Listen for remote requests.
            await client.subscribe("+/+/remote")
            async for message in messages:
                # Decode the payload into a configuration object.
                config = decoder(json.loads(message.payload))
                remote_topic = "/".join(message.topic.split("/")[:-1])

                # Tell the manager to configure a new bridge.
                await mng.configure(config, remote_topic)


async def publisher(publish_queue):
    async with Client("localhost") as client:
        while True:
            # Wait for message we have to relay.
            topic, payload = await publish_queue.get()
            # Publish the message locally.
            await client.publish(topic, payload)


async def main():
    # Create a publish queue and the publisher.
    publish_queue = asyncio.Queue()
    publisher_task = asyncio.create_task(publisher(publish_queue))

    # Create the subscribe manager and the configuration subscriber.
    mng = SubscribeManager(publish_queue)
    config_task = asyncio.create_task(config_sub(mng))

    # Wait for both tasks to end (which will never happen)
    await asyncio.wait([publisher_task, config_task])


if __name__ == "__main__":
    asyncio.run(main())
