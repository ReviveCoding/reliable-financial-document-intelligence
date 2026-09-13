from __future__ import annotations

import os
import signal
import time
from pathlib import Path

from rfdi_v3.runtime import RuntimeStore, Worker


root = Path(os.environ.get("RFDI_V3_SERVICE_ROOT", "/runtime"))
worker = Worker(RuntimeStore(root))
worker.start()
signal.signal(signal.SIGTERM, lambda *_: worker.stop())
signal.signal(signal.SIGINT, lambda *_: worker.stop())
while worker.thread.is_alive():
    time.sleep(1)
