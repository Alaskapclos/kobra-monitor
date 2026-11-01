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

Existing camera and grid regression checks also passed. This validates the server HTTP/session path with synthetic inputs. Simultaneous real-browser use, mobile background behavior, real FLV inputs and FFmpeg load remain separate practical checks.
