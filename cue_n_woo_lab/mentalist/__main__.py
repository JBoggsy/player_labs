"""Entry point: `python -m mentalist` (the image's CMD)."""
import asyncio

from .player import main

asyncio.run(main())
