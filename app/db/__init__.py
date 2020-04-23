import os
from databases import Database
from sqlalchemy import MetaData, create_engine
from .EnumTypes import PermissionLevel, TaskTypes

database = Database(
    os.getenv('DATABASE_URL', 'postgresql://<user>:<password>@localhost/<db-name>')
)

engine = create_engine(str(database.url))
metadata = MetaData(bind=engine)

# These need to be imported after the engine has been created
from .Users import users
from .Tasks import tasks

metadata.create_all(engine)
