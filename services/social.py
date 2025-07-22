from typing import Dict
from authlib.integrations.httpx_client import OAuth2Client

from utils.settings import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

FACEBOOK_AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
FACEBOOK_TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
FACEBOOK_USERINFO_URL = "https://graph.facebook.com/me"


def _google_client() -> OAuth2Client:
    return OAuth2Client(
        settings.google_client_id,
        settings.google_client_secret,
        scope="openid email profile",
        redirect_uri=settings.google_redirect_uri,
    )


def _facebook_client() -> OAuth2Client:
    return OAuth2Client(
        settings.facebook_client_id,
        settings.facebook_client_secret,
        scope="email public_profile",
        redirect_uri=settings.facebook_redirect_uri,
    )


def get_client(provider: str) -> OAuth2Client:
    if provider == "google":
        return _google_client()
    if provider == "facebook":
        return _facebook_client()
    raise ValueError("Unsupported provider")


def generate_login_url(provider: str) -> str:
    client = get_client(provider)
    if provider == "google":
        authorize_url = GOOGLE_AUTH_URL
    else:
        authorize_url = FACEBOOK_AUTH_URL
    url, _ = client.create_authorization_url(authorize_url)
    return url


def fetch_user_info(provider: str, code: str) -> Dict[str, str]:
    client = get_client(provider)
    if provider == "google":
        token = client.fetch_token(GOOGLE_TOKEN_URL, code=code)
        resp = client.get(GOOGLE_USERINFO_URL, token=token)
        resp.raise_for_status()
        data = resp.json()
        return {
            "email": data.get("email"),
            "social_id": data.get("sub"),
            "avatar_url": data.get("picture"),
            "full_name": data.get("name"),
        }
    if provider == "facebook":
        token = client.fetch_token(FACEBOOK_TOKEN_URL, code=code)
        resp = client.get(
            FACEBOOK_USERINFO_URL,
            params={"fields": "id,name,email,picture.type(large)"},
            token=token,
        )
        resp.raise_for_status()
        data = resp.json()
        picture = data.get("picture", {}).get("data", {}).get("url")
        return {
            "email": data.get("email"),
            "social_id": data.get("id"),
            "avatar_url": picture,
            "full_name": data.get("name"),
        }
    raise ValueError("Unsupported provider")
