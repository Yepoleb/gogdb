import urllib.parse
import json
from datetime import datetime, timezone, timedelta
import asyncio
import aiohttp



GALAXY_ID = "46899977096215655"
GALAXY_SECRET = "9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9"

REDIRECT_URL = "https://embed.gog.com/on_login_success?origin=client"
AUTH_URL = "https://auth.gog.com/auth?client_id={client_id}&redirect_uri={redir_uri}&response_type=code&layout=client2"
TOKEN_URL = "https://auth.gog.com/token"

class AuthError(Exception):
    pass

def get_auth_url(client_id=GALAXY_ID):
    redirect_url_quoted = urllib.parse.quote(REDIRECT_URL)
    return AUTH_URL.format(client_id=client_id, redir_uri=redirect_url_quoted)


class GogToken:
    def __init__(self, aio_session, client_id=GALAXY_ID, client_secret=GALAXY_SECRET):
        self.aio_session = aio_session
        self.client_id = client_id
        self.client_secret = client_secret

        self.lock = asyncio.Lock()

    @classmethod
    def from_file(cls, aio_session, filename):
        token = cls(aio_session)
        token.load(filename)
        return token

    @classmethod
    async def from_code(cls, aio_session, login_code, client_id=GALAXY_ID, client_secret=GALAXY_SECRET):
        token_query = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": login_code,
            "redirect_uri": REDIRECT_URL # Needed for origin verification
        }
        token_resp = await aio_session.get(TOKEN_URL, params=token_query)
        token = cls(aio_session, client_id, client_secret)
        token.set_data(await token_resp.json())
        return token

    def set_data(self, token_data):
        if "error" in token_data:
            raise AuthError(token_data["error"], token_data["error_description"])

        if "client_id" in token_data:
            self.client_id = token_data["client_id"]
        if "client_secret" in token_data:
            self.client_secret = token_data["client_secret"]
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data["refresh_token"]
        self.expires_in = timedelta(seconds=token_data["expires_in"])
        self.scope = token_data["scope"]
        self.session_id = token_data["session_id"]
        self.token_type = token_data["token_type"]
        self.user_id = token_data["user_id"]
        if "created" in token_data:
            self.created = datetime.fromtimestamp(
                token_data["created"], tz=timezone.utc)
        else:
            self.created = datetime.now(tz=timezone.utc)

    def get_data(self):
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": int(self.expires_in.total_seconds()),
            "scope": self.scope,
            "session_id": self.session_id,
            "token_type": self.token_type,
            "user_id": self.user_id,
            "created": int(self.created.timestamp())
        }
        return token_data

    def load(self, filename):
        with open(filename, "r") as f:
            self.set_data(json.load(f))

    def save(self, filename):
        with open(filename, "w") as f:
            json.dump(self.get_data(), f, indent=2, sort_keys=True)

    async def refresh(self, refresh_token=None):
        if refresh_token is None:
            refresh_token = self.refresh_token
        token_query = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        token_resp = await self.aio_session.get(TOKEN_URL, params=token_query)
        self.set_data(await token_resp.json())

    def expired(self, margin=timedelta(seconds=60)):
        expires_at = self.created + self.expires_in
        return (datetime.now(timezone.utc) - expires_at) > margin

    async def refresh_if_expired(self, refresh_token=None, margin=timedelta(seconds=60)):
        await self.lock.acquire()
        expired = self.expired(margin)
        if expired:
            await self.refresh(refresh_token)
        self.lock.release()
        return expired

    def __repr__(self):
        return repr(self.__dict__)

async def main():
    import re
    import sys

    LOGIN_INSTRUCTIONS = \
    "Please open {auth_url} and login to gog.com. After completing the login " \
    "you will be redirected to a blank page. Copy the full URL starting with " \
    "https://embed.gog.com/on_login_success and paste it into this window."

    LOGIN_CODE_RE = re.compile(r"code=([\w\-]+)")

    if len(sys.argv) < 2:
        print("Usage: {} <token.json>".format(sys.argv[0]))
        return 1
    token_filepath = sys.argv[1]

    print(LOGIN_INSTRUCTIONS.format(auth_url=get_auth_url()))
    login_url = input("Login URL: ")
    code_match = LOGIN_CODE_RE.search(login_url)
    if code_match is None:
        print("Error: Could not find a login code in the provided URL")
        return 1
    login_code = code_match.group(1)

    async with aiohttp.ClientSession() as aio_session:
        token = await GogToken.from_code(aio_session, login_code)
        token.save(token_filepath)
    print("Token saved at", token_filepath)
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
