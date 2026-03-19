import logging
import os
from pathlib import Path

import nxt

log = logging.getLogger(__name__)

YRIG_NXT_DIR = Path(__file__).parents[3] / "nxt"
os.environ["YRIG_NXT_DIR"] = str(YRIG_NXT_DIR.resolve())


def execute_nxt_graph(filepath: Path):
    nxt.execute_graph(str(filepath))
