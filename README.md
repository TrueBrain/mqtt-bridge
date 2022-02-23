# MQTT Bridge

Sometimes you have two MQTT brokers, and you want one to contain information about the other.

This bridge allows you to dynamically (over MQTT) tell what information it should fetch from what remote MQTT broker to duplicate in the local MQTT broker.

# Usage

```bash
python3 -m venv .env
.env/bin/pip install -U "setuptools<50" pip
.env/bin/pip install -e .

.env/bin/python -m mqtt_bridge
```

This will connect to the MQTT broker on localhost (default port), and starts listening for `+/+/remote`.
If a key matching is created, the following payload is expected:

```json
{
    "remote": "ip:port",
    "on_initialize": "",
    "on_disconnect": "",
}
```

- `remote`: the remote broker to connect to. `port` part is mandatory, so use 1883 for default port.
- `on_initialize`: the initial payload when we haven't seen any payload on the remote yet.
- `on_disconnect`: the payload to use locally when the connection to the remote broker drops.

After this, the bridge will connect to the remote broker and starts listening for activity on the `+/+` topic.
Anything it sees there, will be replicated on the local broker.

# Example setup

- Run an MQTT broker on 1883.
- Run an MQTT broker on 1900.
- Start `test_receive.py`.
- Start `test_send.py`. both should show nothing.
- Start the bridge, and (re)start `test_receive.py`. You now should see data from `test_receive.py`.
