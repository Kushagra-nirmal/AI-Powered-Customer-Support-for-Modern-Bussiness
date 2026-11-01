"""Application runner with proper Windows event loop configuration for psycopg async pool."""

import os
import sys
import asyncio
import uvicorn
import uvicorn.loops.asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        backlog=4096,
        limit_concurrency=2000,
        timeout_keep_alive=30,
        loop="asyncio",
    )
