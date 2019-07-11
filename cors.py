from functools import wraps

from flask import make_response


def add_response_headers(headers={}):
    """This decorator adds the headers passed in to the response"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp

        return decorated_function

    return decorator


def enable_cors_for_post(f):
    @wraps(f)
    @add_response_headers({'Access-Control-Allow-Origin': 'https://mysterium.network'})
    @add_response_headers({'Access-Control-Allow-Methods': 'POST'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated_function
