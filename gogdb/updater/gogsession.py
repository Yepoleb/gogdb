import pathlib
import logging
import json
import zlib
import os
import traceback
import asyncio

import aiohttp

import gogdb.core.storage as storage
from gogdb.updater.gogtoken import GogToken



CLIENT_VERSION = "1.2.17.9" # Just for their statistics
USER_AGENT = f"GOGGalaxyClient/{CLIENT_VERSION} gogdb/2.0"
REQUEST_RETRIES = 3

# Caching constants
CACHE_NONE = 0      # Download without caching
CACHE_STORE = 1     # Download and store to disk
CACHE_LOAD = 2      # Only load from disk
CACHE_FALLBACK = 3  # Try to load, on failure fall back to store

logger = logging.getLogger("UpdateDB.session")

class GogSession:
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.storage_path = pathlib.Path(config["STORAGE_PATH"])
        aio_connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        headers = {"User-Agent": USER_AGENT}
        self.aio_session = aiohttp.ClientSession(
            connector=aio_connector, headers=headers)
        self.set_cookie("gog_lc", "US_USD_en-US")
        self.load_token()

    def load_token(self):
        self.token = GogToken(self.aio_session)
        self.token.set_data(self.db.token.load())

    def save_token(self):
        self.db.token.save(self.token.get_data())

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
        kwargs["timeout"] = aiohttp.ClientTimeout(total=kwargs.get("timeout", 10))
        retries = REQUEST_RETRIES
        while retries > 0:
            try:
                resp = await self.aio_session.get(*args, **kwargs)
            except asyncio.TimeoutError:
                retries -= 1
                if retries > 0:
                    continue
                else:
                    raise
            if resp.status < 500:
                break
            await resp.read()
            retries -= 1
        return resp

    async def get_json(self, name, url, path, caching=CACHE_NONE, decompress=False, expect_404=False, **kwargs):
        logger.debug("Requesting %r", url)
        if caching & CACHE_LOAD:
            try:
                with open(path, "r") as load_file:
                    logger.debug("Served from cache %s", path)
                    return json.load(load_file)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                if caching == CACHE_LOAD:
                    return None
                else:
                    pass # Continue downloading

        try:
            resp = await self.retry_get(url, **kwargs)
        except Exception as e:
            logger.error("Failed to load %s: %s", name, traceback.format_exception_only(e)[-1].strip())
            return
        if resp.status >= 400:
            # Treat 404s as info because they are so common
            if resp.status == 404 and expect_404:
                logger.info("Request for %s returned %s", name, resp.status)
            else:
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

    async def fetch_product_v0(self, prod_id):
        return await self.get_json(
            f"api v0 {prod_id}",
            url=f"https://api.gog.com/products/{prod_id}?expand=downloads,expanded_dlcs,description,screenshots,videos,related_products,changelog&locale=en-US",
            path=self.storage_path / f"raw/prod_v0/{prod_id}_v0.json",
            caching=self.config.get("CACHE_PRODUCT_V0", CACHE_NONE),
            expect_404=True
        )

    async def fetch_product_v2(self, prod_id):
        return await self.get_json(
            f"api v2 {prod_id}",
            url=f"https://api.gog.com/v2/games/{prod_id}?locale=en-US",
            path=self.storage_path / f"raw/prod_v2/{prod_id}_v2.json",
            caching=self.config.get("CACHE_PRODUCT_V2", CACHE_NONE),
            expect_404=True
        )

    async def fetch_builds(self, prod_id, system):
        return await self.get_json(
            f"api v0 {prod_id}",
            url=f"https://content-system.gog.com/products/{prod_id}/os/{system}/builds?generation=2",
            path=self.storage_path / f"raw/builds/{prod_id}_builds_{system}.json",
            caching=self.config.get("CACHE_BUILDS", CACHE_NONE)
        )

    async def fetch_repo_v1(self, repo_url, prod_id, build_id):
        return await self.get_json(
            f"repo v1 {repo_url}",
            url=repo_url,
            path=self.storage_path / f"raw/repo_v1/{prod_id}_{build_id}.json",
            caching=self.config.get("CACHE_REPO_V1", CACHE_NONE)
        )

    async def fetch_manifest_v1(self, mf_name, manifest_url):
        return await self.get_json(
            f"manifest v1 {mf_name}",
            url=manifest_url,
            path=None,
            caching=CACHE_NONE
        )

    async def fetch_repo_v2(self, repo_url, prod_id, build_id):
        return await self.get_json(
            f"repo v2 {repo_url}",
            url=repo_url,
            path=self.storage_path / f"raw/repo_v2/{prod_id}_{build_id}.json",
            caching=self.config.get("CACHE_REPO_V2", CACHE_NONE),
            decompress=True
        )

    async def fetch_manifest_v2(self, manifest_id):
        manifest_url = "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
            manifest_id[0:2], manifest_id[2:4], manifest_id)
        return await self.get_json(
            f"manifest v2 {manifest_id}",
            url=manifest_url,
            path=None,
            caching=CACHE_NONE,
            decompress=True
        )

    async def fetch_catalog(self, params, page_num):
        page_params = params.copy()
        page_params["page"] = page_num
        page_params["limit"] = 48
        cache_id = '_'.join(str(v) for v in page_params.values())
        return await self.get_json(
            f"catalog page {page_num}",
            url="https://catalog.gog.com/v1/catalog",
            params=page_params,
            path=self.storage_path / f"raw/catalog/page_{cache_id}.json",
            caching=self.config.get("CACHE_CATALOG", CACHE_NONE)
        )
