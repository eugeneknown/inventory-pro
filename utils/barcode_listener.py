"""
InventoryPro - Global Barcode Listener
Detects fast keyboard-wedge barcode scanner input and fires a callback.

A barcode scanner acts like a very fast keyboard — it types characters
in rapid succession (< 50ms apart) and ends with a Return key.
This class distinguishes scanner input from human typing using that timing.
"""
import time


class BarcodeListener:
    """
    Attach to any Tkinter widget (typically the root window) to detect
    barcode-scanner input and invoke on_scan(serial: str).

    Usage:
        listener = BarcodeListener(root, on_scan=my_callback)
        listener.start()       # begin listening
        listener.stop()        # stop listening
    """

    # Max milliseconds between keystrokes to be considered a scanner input
    SCAN_THRESHOLD_MS = 50
    # Minimum characters to trigger the callback (avoid accidental Enter presses)
    MIN_LENGTH = 3

    def __init__(self, root, on_scan):
        self._root = root
        self._on_scan = on_scan
        self._buffer = []
        self._last_key_time = 0.0
        self._bind_id = None

    def start(self):
        """Bind the key listener to the root window."""
        self._bind_id = self._root.bind("<Key>", self._on_key, add="+")

    def stop(self):
        """Remove the key listener."""
        if self._bind_id:
            try:
                self._root.unbind("<Key>", self._bind_id)
            except Exception:
                pass
            self._bind_id = None

    def _on_key(self, event):
        """Handle each keystroke — buffer or dispatch."""
        now = time.time() * 1000  # ms

        # Clear buffer if too long since last key (human typing pace)
        if now - self._last_key_time > self.SCAN_THRESHOLD_MS:
            self._buffer.clear()

        self._last_key_time = now

        if event.keysym == "Return":
            scanned = "".join(self._buffer).strip()
            self._buffer.clear()
            if len(scanned) >= self.MIN_LENGTH:
                # Use after(0) so the callback runs safely on the main Tkinter thread
                self._root.after(0, lambda s=scanned: self._on_scan(s))
            return

        # Ignore modifier-only keys
        if event.char and event.char.isprintable():
            self._buffer.append(event.char)
