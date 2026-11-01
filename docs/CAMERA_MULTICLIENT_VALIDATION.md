# Camera multi-client validation

An isolated loopback HTTP check used synthetic JPEG readers and two independent authenticated sessions. No printer connection, production data or production service changes were involved.

Passed scenarios:

- Anonymous requests do not create readers.
- Both sessions share one reader for the same camera.
- An invalid CSRF value cannot release either view.
- The four-camera limit applies across sessions.
- Closing one view preserves frames for the remaining view.
- Released capacity can be reused.
- Expired inactive views do not interrupt an active view.
- Closing the final view stops the reader; reopening supplies frames again.

Existing camera and grid regression checks also passed. This validates the server HTTP/session path with synthetic inputs. Mobile background behavior and prolonged FFmpeg load remain separate practical checks.

## Real desktop browser follow-up

Chrome on a LAN origin and an independent browser on an HTTPS origin displayed changing live frames from the same stock printer concurrently. Both images decoded at 1280 by 720 pixels. Closing the first view preserved image updates in the second. Reopening the first as a two-camera overview also worked; closing the second preserved updates in both overview tiles. Views were closed afterward.

This was a bounded desktop check against the existing read-only service, without updates, restarts or printer commands. It does not establish long-term load tolerance, a four-printer real fleet, mobile background behavior or image quality under every network condition.
