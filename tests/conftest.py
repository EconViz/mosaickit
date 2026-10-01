"""Keep renderer tests headless on every supported platform."""

import os

os.environ.setdefault("MPLBACKEND", "Agg")
