import jwt
import os
import uuid

from datetime import datetime

from typing import Dict, Union, List

from app.db import TaskTypes
from . import BaseMediator
from . import users

from sqlalchemy.sql import select, insert

import google.oauth2.credentials


class AuthMediator(BaseMediator):
    '''
    Mediator to track login and user creation tasks

    Attributes:
    -----------
        hermes_user: Dict[str, any]
            User authenticated through JWT and stored / retrieved from Postgres

    Methods:
    --------
        handleJWT(self, access_token: str) -> AuthMediator:
            Takes a JWT access token and attempts to retrieve the user from
            Postgres. If the user isn't there, create a new user. Either way,
            store the resulting user as an instance attribute and return self.

    '''

    __slots__ = ['hermes_user']

    def __init__(self,
                 database: 'Postgres',
                 user_uuid: str,
                 TaskType: TaskTypes
                 ) -> None:

        super().__init__(database, user_uuid, TaskType)
        self.hermes_user = {}

    @property
    def credentials(self) -> Dict[str, Union[str, List[str]]]:
        if not self.hermes_user:
            return {}

        creds = {'token': self.hermes_user['token'],
                 'refresh_token': self.hermes_user['refresh_token'],
                 'token_uri': self.hermes_user['token_uri'],
                 'client_id': self.hermes_user['client_id'],
                 'client_secret': self.hermes_user['client_secret'],
                 'scopes': self.hermes_user['scopes']}


        return google.oauth2.credentials.Credentials(**creds)


    async def handleJWT(self, access_token: str) -> 'AuthMediator':
        ''' Wraps the logic of finding or creating a User'''

        jwt_user = jwt.decode(access_token, os.getenv('JWT_SECRET', None))
        query = 'SELECT * FROM users WHERE users.email = :email'
        pg_user = await self.database.fetch_one(
            query=query,
            values={'email': jwt_user.get('email')}
        )

        if not pg_user:
            await self.createNewUser(jwt_user)

        else:
            # Otherwise, set the user id as an instance attribute
            # and track the login time for that user
            self.user_uuid = str(pg_user['id'])
            await self._track_login()

            self.hermes_user = pg_user

        return self

    async def createNewUser(self, jwt_user: Dict[str, Union[str, int]]) -> None:
        # If no user is found, create a new User uuid and change the task_type
        # to NEW USER and initialize a wrapper to track the task of
        # creating a new user
        user_uuid = uuid.uuid4()
        self.user_uuid = str(user_uuid)
        self.task_type = TaskTypes['NEW_USER']

        try:
            insert_stmt = '''
            INSERT INTO users
            VALUES(:id, :email, :name, :permission, :verified, :phone, :last_fetch)
            '''
            new_user = {"id": self.user_uuid, 'email': jwt_user['email'],
                        'name': jwt_user['name'], 'permission': 'BASE',
                        'verified': jwt_user['verified'], 'phone': jwt_user['phone'],
                        'last_fetch': datetime.now()}

            await self.database.execute(
                query=insert_stmt,
                values=new_user
            )

            self.hermes_user = new_user
            await self._track_login()

        except Exception as e:
            self._update_errors(e)

        return

    async def updateCredentials(self, creds: Dict[str, Union[str, List[str]]]) -> 'AuthMediator':
        try:
            update_user = self.table_refs['users'].update(). \
                where(self.table_refs['users'].c.id == self.user_uuid). \
                values(
                    token=creds['token'],
                    refresh_token=creds['refresh_token'],
                    token_uri=creds['token_uri'],
                    client_id=creds['client_id'],
                    client_secret=creds['client_secret'],
                    scopes=creds['scopes']
            )

            await self.database.execute(update_user)

        except Exception as e:
            self._update_errors(e)

        await self._finalize_task()

        return self
