import os
import jwt
import json

from functools import wraps
from sanic.response import redirect

import google.oauth2.credentials

from app.db import users, TaskTypes
from app.workers.mediators import AuthMediator


def authorized():
    '''
    Decorator that redirects to /authorize endpoint if there are no credentials in the session. Otherwise it proceeds as usual.
    '''
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            # Grab the creds from the session
            # Todo: maybe store this ish in postgres
            creds = request['session'].get('credentials', None)

            if not creds:
                return redirect('/authorize')
            else:
                is_authorized = True

            if is_authorized:
                try:
                    credentials = google.oauth2.credentials.Credentials(**creds)

                    # the user is authorized.
                    # run the handler method and return the response
                    response = await f(request, credentials, *args, **kwargs)
                    return response

                except Exception as e:
                    return json({
                        'status': 'Error',
                        'error': f'something went wrong: {e}'
                    }, 500)
            else:
                return json({'status': 'not_authorized'}, 403)

        return decorated_function
    return decorator

def withOauth():
    '''
    Decorator that redirects to NEXT app if there isn't a JWT token present
    '''
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            # run some method that checks the request
            # for the client's authorization status
            is_authorized = False
            msg_body = json.loads(request.body)
            if not msg_body.get('token', None):
                return json({'status': 'Not Authorized'}, 401)

            try:
                token = msg_body.get('token', None)

                authenticator = AuthMediator(
                    request.app.database,
                    '',
                    TaskTypes['AUTHENTICATE']
                )
                auth_obj = await authenticator.handleJWT(token)

                if auth_obj.successful:
                    is_authorized = True
                else:
                    return redirect('http://localhost:3000/api/authorize')

            except Exception as e:
                return json({
                    'status': 'Error',
                    'message': f'Error authenticating user: {e}'
                }, 500)

            if is_authorized:
                response = await f(request, auth_obj, *args, **kwargs)
                return response
            else:
                return json({'status': 'not_authorized'}, 403)
        return decorated_function
    return decorator
