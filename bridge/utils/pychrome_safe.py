import json

import websocket
from pychrome.tab import Tab


def _safe_recv_loop(self):
    """
    Replacement for pychrome.Tab._recv_loop that silences benign websocket
    shutdowns instead of logging a noisy traceback.

    The original implementation logs with exc_info=True on any
    websocket.WebSocketException / OSError, which prints the full stack trace.
    Here we keep the same behavior minus the logging.
    """
    while not self._stopped.is_set():
        try:
            self._ws.settimeout(1)
            message_json = self._ws.recv()
            try:
                message = json.loads(message_json)
            except json.decoder.JSONDecodeError:
                # Ignore malformed JSON frames silently.
                continue
        except websocket.WebSocketTimeoutException:
            # Idle timeout, keep looping.
            continue
        except (websocket.WebSocketException, OSError):
            # Remote websocket closed or other network issue: stop quietly.
            if not self._stopped.is_set():
                self._stopped.set()
            return

        # From here on we mirror pychrome's logic, without any extra logging.
        if self.debug:  # pragma: no cover
            print('< RECV %s' % message_json)

        if "method" in message:
            self.event_queue.put(message)

        elif "id" in message and message["id"] in self.method_results:
            self.method_results[message['id']].put(message)


# Apply monkeypatch
Tab._recv_loop = _safe_recv_loop

# Sanity check: ensure the monkeypatch is really applied
assert Tab._recv_loop is _safe_recv_loop
