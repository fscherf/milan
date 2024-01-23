import concurrent
import threading
import logging
import asyncio

default_logger = logging.getLogger('background-loop')


class BackgroundLoop:
    def __init__(self, logger=default_logger):
        self.logger = default_logger

        self.loop = None
        self._started = concurrent.futures.Future()
        self._stopped = None

        # start loop thread
        self.thread = threading.Thread(target=self._run_loop)

        self.thread.start()

        # wait for loop to start
        self._started.result()

    def __repr__(self):
        logger = self.logger
        running = self._started.done() and not self._stopped.done()

        return f'<{self.__class__.__name__}({logger=}, {running=})>'

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()

        asyncio.set_event_loop(self.loop)

        try:
            main_task = self.loop.create_task(
                coro=self._main(),
                name='main',
            )

            self.loop.run_until_complete(main_task)

        except asyncio.CancelledError:
            self.logger.debug(
                'CancelledError was thrown while loop was running',
            )

        finally:
            self.loop.stop()
            self.loop.close()

    async def _main(self):
        self._stopped = asyncio.Future()
        self._started.set_result(None)

        # main loop
        await self._stopped

        # shutdown
        # cancel tasks
        canceled_tasks = []
        current_task = asyncio.current_task(loop=self.loop)

        for task in asyncio.all_tasks():
            if task.done() or task is current_task:
                continue

            task.cancel()
            canceled_tasks.append(task)

        for task in canceled_tasks:
            try:
                await task

            except asyncio.CancelledError:
                self.logger.debug(
                    'CancelledError was thrown while shutting down %s',
                    task,
                )

    def stop(self):
        async def _stop():
            self._stopped.set_result(None)

        if self._stopped.done():
            raise RuntimeError('loop is already stopped')

        concurrent_future = asyncio.run_coroutine_threadsafe(
            coro=_stop(),
            loop=self.loop,
        )

        return concurrent_future.result()
