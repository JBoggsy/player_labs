"""Entry point: `python -m cheater` (the image's CMD)."""
import asyncio

from .player import main

asyncio.run(main())
