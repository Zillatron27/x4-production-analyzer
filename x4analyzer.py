#!/usr/bin/env python3
"""
X4 Empire Production Analyzer
Main executable script
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from x4analyzer.app import main

if __name__ == "__main__":
    main()
