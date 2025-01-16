import asyncio
import websockets
import logging
import signal
import psutil  # For optional system metrics

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websockets")

# 127.0.0.1:8009
"""
websocket = connect("ws://127.0.0.1:8009")
websocket.send("Hello world!")
message = websocket.recv()
print(message)
"""

_PORT = 8000
_HOST = "0.0.0.0"


async def echo_handler(websocket, path):
    try:
        async for message in websocket:
            await websocket.send(message)

            # Optional: Log system metrics
            if message == "system_metrics":
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                await websocket.send(f"CPU: {cpu_percent}%, Memory: {memory_percent}%")

    except websockets.ConnectionClosed:
        logger.info(f"Client disconnected: {websocket.remote_address}")


async def main():
    # Bind to all interfaces
    async with websockets.serve(echo_handler, _HOST, _PORT):
        await asyncio.Future()  # Run forever


def graceful_shutdown(sig, loop):
    logger.info(f"Received signal {sig.name}, shutting down...")
    tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    loop.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    signals = (signal.SIGINT, signal.SIGTERM)
    for sig in signals:
        loop.add_signal_handler(sig, graceful_shutdown, sig, loop)

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
        logger.info("Server shutdown complete.")
