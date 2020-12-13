
class GogSession:
    def __init__(self):
        aio_connector = aiohttp.TCPConnector(limit=10, limit_per_host=4)
        headers = {"User-Agent": USER_AGENT}
        self.aio_session = aiohttp.ClientSession(
            connector=aio_connector, headers=headers)
        self.set_cookie("gog_lc", "US_USD_en-US")
        self.load_token()

    def load_token(self):
        self.token = GogToken(self.aio_session)
        self.token.set_data(db.token.load())

    def save_token(self):
        db.token.save(self.token.get_data())

    def set_cookie(self, name, value):
        self.aio_session.cookie_jar.update_cookies({name: value})

    async def close(self):
        await self.aio_session.close()

    async def retry_get(self, *args, **kwargs):
        headers = kwargs.get("headers", {})
        if await self.token.refresh_if_expired():
            self.save_token()
        headers["Authorization"] = "Bearer " + self.token.access_token
        kwargs["headers"] = headers
        # Set default timeout
        kwargs["timeout"] = kwargs.get("timeout", 10)
        retries = REQUEST_RETRIES
        while retries > 0:
            resp = await self.aio_session.get(*args, **kwargs)
            if resp.status < 500:
                break
            await resp.read()
            retries -= 1
        return resp

    async def get_json(self, name, url, path, caching=CACHE_NONE, decompress=False, **kwargs):
        logger.debug("Requesting %r", url)
        if caching & CACHE_LOAD:
            try:
                with open(path, "r") as load_file:
                    logger.debug("Served from cache %r", url)
                    return json.load(load_file)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                if caching == CACHE_LOAD:
                    return None
                else:
                    pass # Continue downloading

        try:
            resp = await self.retry_get(url, **kwargs)
        except Exception as e:
            logger.error("Failed to load %s: %r", name, e)
            return
        if resp.status >= 400:
            logger.error("Request for %s returned %s", name, resp.status)
            await resp.read()
            return
        try:
            if decompress:
                content_comp = await resp.read()
                content_binary = zlib.decompress(content_comp, wbits=15)
                content_text = content_binary.decode("utf-8")
            else:
                content_text = await resp.text()
        except Exception as e:
            logger.error("Failed to read response content for %s: %r", name, e)
            return

        try:
            content_json = json.loads(content_text)
        except Exception as e:
            logger.error("Failed to decode json for %s: %r", name, e)
            return

        if caching & CACHE_STORE:
            path.parent.mkdir(parents=True, exist_ok=True)
            path_dst = str(path)
            path_temp = path_dst + ".part"
            with open(path_temp, "w") as store_file:
                storage.json_dump(content_json, store_file)
            os.replace(path_temp, path_dst)

        return content_json
