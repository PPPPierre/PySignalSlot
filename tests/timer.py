import sys
import os
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from src.signal_slot import AsyncTimer

async def timeout_callback():
    print('echo!')

async def main():
    print('\nFirst example:')
    timer = AsyncTimer(1, timeout_callback, once=True)  # set timer for two seconds
    await asyncio.sleep(2.5)  # wait to see timer works

    print('\nSecond example:')
    timer = AsyncTimer(1, timeout_callback, once=False)  # set timer for two seconds
    print(asyncio.all_tasks())
    await asyncio.sleep(10)
    timer.cancel()  # cancel it
    await asyncio.sleep(5)  # and wait to see it won't call callback

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(main())
finally:
    loop.run_until_complete(loop.shutdown_asyncgens())
