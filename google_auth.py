
import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

def configure_google_oauth():
    """
    Configures Google OAuth 2.0 for the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """
    config = Config('.env')
    oauth = OAuth(config)

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    oauth.register(
        name='google',
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    return oauth
