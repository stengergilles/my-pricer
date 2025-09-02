from flask_restful import Resource
from web.backend.auth.middleware import requires_auth

class AuthenticatedResource(Resource):
    method_decorators = [requires_auth()]