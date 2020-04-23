import asyncio
from typing import List, Tuple, Generator, Dict, Optional

from functools import partial

from .mediators import DBMediator, GraphMediator

from . import users, tasks, TaskTypes

async def create_task_queue(app, loop):
    app.queue = asyncio.Queue(loop=loop, maxsize=app.config.MAX_QUEUE_SIZE)

    async def db_callback(
        row_generators: List[Tuple[str, Generator[Dict[str, 'Table'], None, None]]],
        user_uuid: str,
        update_graph: Optional[bool] = True,
        *args,
        **kwargs
    ) -> str:

        mediator = DBMediator(app.database, user_uuid, TaskTypes['DB_INSERT'])
        init_db_mediator = await mediator._async_init()
        mediated_db_task = partial(init_db_mediator.handleDbInserts, row_generators)

        # Add the job to the queue
        await app.queue.put(mediated_db_task)

        return init_db_mediator.task_uuid

    # Workers to handle updating the DB
    for i in range(4):
        app.add_task(
            db_worker(
                f"DB-Worker-{i}",
                app.queue
            )
        )
