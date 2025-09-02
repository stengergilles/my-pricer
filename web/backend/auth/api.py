from flask_restful import Api
from web.backend.auth.middleware import requires_auth

class AuthenticatedApi(Api):
    def add_resource(self, resource, *urls, **kwargs):
        resource.method_decorators = [requires_auth()]
        super().add_resource(resource, *urls, **kwargs)
