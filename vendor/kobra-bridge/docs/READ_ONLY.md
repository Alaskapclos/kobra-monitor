# Read-only mode

Enable at process startup using `--read-only`, `READ_ONLY=1`, or
`read_only = 1` in the `[bridge]` section of `config/config.ini`.
The setting applies to every printer in this bridge process. Disable only by
changing startup configuration and restarting; the web settings API is blocked.
Invalid boolean configuration values fail startup instead of silently enabling
control. Existing installations remain unchanged unless the mode is enabled.

For example, with the existing printer credentials and TLS certificate files
configured as documented in README.md:

```sh
python kobrax_moonraker_bridge.py --read-only --host 127.0.0.1 --port 7125
```

`GET /` returns the mode and supported endpoints instead of the control UI.
`GET /api/state` includes `read_only: true`. Available GET endpoints:

- `/server/info`
- `/health`
- `/printer/info`
- `/printer/objects/list`
- `/printer/objects/query?extruder&heater_bed&print_stats&display_status`
- `/api/state`

All other HTTP paths/methods, including WebSocket upgrades, return 403 before
a handler runs. This deliberately restricts UI, Orca, and general Moonraker
client compatibility: clients needing WebSocket subscriptions cannot use this
mode. Use the HTTP status endpoints for monitoring. `/printer/info` and
`/server/info` retain the existing emulated compatibility metadata; use
`print_stats` and `/api/state` for actual print status.

The MQTT client accepts only `info/query`, `status/query`, `print/query`,
`tempature/query`, and `multiColorBox/getInfo`, with `data: null`, on the exact
device's web/slicer topics. The final socket-write path also validates complete
single-packet framing, preventing bypass through a raw publish, a different
device/topic, QoS/retained packets, or concatenated packets. MQTT authentication,
the device report subscription and keepalive remain available. The LAN
authentication handshake establishes a session; read-only here means no device
control/settings/file actions.

HTTP uploads are blocked independently in the MQTT client's upload method.
Automatic camera start/stream setup, ACE tip forming and Spoolman writes are
disabled even if their normal configuration requests them. Incoming reports
continue to update the status cache. The mode is a control boundary inside this
process, not an OS security boundary against modifying the program or accessing
the printer from another process. Existing TLS verification behavior is unchanged.

Run `python test_read_only.py` for offline regression tests, or `sh test.sh` for
the existing suite plus these tests. The offline tests use fake sockets and never
connect to a printer. No HTTP or MQTT control operation is needed for verification.
