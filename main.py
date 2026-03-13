"""
ME17Suite
Bosch ME17.8.5 by Rotax — Binary Editor
"""

import sys
from pathlib import Path

# Dodaj root folder u Python path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import run

if __name__ == "__main__":
    sys.exit(run())