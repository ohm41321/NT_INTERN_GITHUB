import os
from authlib.integrations.starlette_client import OAuth

# Load environment variables
LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# Initialize OAuth
oauth = OAuth()

# Configure Line OAuth manually to enforce HS256 algorithm support
oauth.register(
    name='line',
    client_id=LINE_CHANNEL_ID,
    client_secret=LINE_CHANNEL_SECRET,
    access_token_url='https://api.line.me/oauth2/v2.1/token',
    authorize_url='https://access.line.me/oauth2/v2.1/authorize',
    client_kwargs={
        'scope': 'openid profile email'
    },
    server_metadata={
        'issuer': 'https://access.line.me',
        'token_endpoint': 'https://api.line.me/oauth2/v2.1/token',
        'authorization_endpoint': 'https://access.line.me/oauth2/v2.1/authorize',
        # This is the crucial part to force acceptance of HS256
        'id_token_signing_alg_values_supported': ['HS256'],
    }
)
