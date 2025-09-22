import pathlib
import logging
import json
import zlib
import os
import traceback
import asyncio

import aiohttp
import aiofiles

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

def short_exception(e):
    return traceback.format_exception_only(e)[-1].strip()

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
        self.token = None # Needs to be loaded with load_token

    async def load_token(self):
        self.token = GogToken(self.aio_session)
        self.token.set_data(await self.db.token.load())

    async def save_token(self):
        await self.db.token.save(self.token.get_data())

    def set_cookie(self, name, value):
        self.aio_session.cookie_jar.update_cookies({name: value})

    async def close(self):
        await self.aio_session.close()

    async def get_json(self, name, url, headers=None, timeout_sec=10, decompress=False, expect_404=False, **kwargs):
        if await self.token.refresh_if_expired():
            await self.save_token()

        if headers is None:
            headers = {}
        headers["Authorization"] = "Bearer " + self.token.access_token
        # Set default timeout
        timeout = aiohttp.ClientTimeout(total=timeout_sec)
        retries = REQUEST_RETRIES
        while retries > 0:
            retries -= 1
            try:
                resp = await self.aio_session.get(url, headers=headers, timeout=timeout, **kwargs)
            except (TimeoutError, aiohttp.ClientError) as e:
                if retries == 0:
                    logger.error("Failed to request %s: %s", name, short_exception(e))
                    return
                else:
                    continue
            except Exception as e:
                logger.error("Failed to request %s: %s", name, short_exception(e))
                return

            if 200 <= resp.status < 300:
                try:
                    if decompress:
                        content_comp = await resp.read()
                        content_binary = zlib.decompress(content_comp, wbits=15)
                        content_text = content_binary.decode("utf-8")
                    else:
                        content_text = await resp.text()
                except (TimeoutError, aiohttp.ClientError) as e:
                    if retries == 0:
                        logger.error(
                            "Failed to read request body of %s: %s", name, short_exception(e)
                        )
                        return
                    else:
                        continue
                except Exception as e:
                    logger.error("Failed to read request body of %s: %s", name, short_exception(e))
                    return

                try:
                    content_json = json.loads(content_text)
                except json.JSONDecodeError as e:
                    if retries == 0:
                        logger.error("Failed to decode json of %s: %s", name, short_exception(e))
                        return
                    else:
                        continue
                except Exception as e:
                    logger.error("Failed to decode json of %s: %s", name, short_exception(e))
                    return
                return content_json

            # Treat 404s as info because they are so common
            elif resp.status == 404 and expect_404:
                logger.info("Request for %s returned %s", name, resp.status)
                await resp.read()
                return
            # Status 400 is more likely to be a server error than a client error, retry
            # 408 is request timeout
            elif 401 <= resp.status < 500 and resp.status != 408:
                logger.error("Request for %s returned %s", name, resp.status)
                await resp.read()
                return

        logger.info("Request for %s returned %s", name, resp.status)
        # Function regularly ends with `return content_json`

    async def get_json_cached(self, name, url, path, caching=CACHE_NONE, **kwargs):
        if "params" in kwargs:
            logger.debug("Requesting %r %r", url, kwargs["params"])
        else:
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

        content_json = await self.get_json(name, url, **kwargs)
        if content_json is None:
            return

        if caching & CACHE_STORE:
            path.parent.mkdir(parents=True, exist_ok=True)
            path_dst = str(path)
            path_temp = path_dst + ".part"
            async with aiofiles.open(path_temp, "w") as store_file:
                await store_file.write(json.dumps(
                    content_json, indent=2, sort_keys=True, ensure_ascii=False))
            os.replace(path_temp, path_dst)

        return content_json

    async def fetch_product_v0(self, prod_id):
        return await self.get_json_cached(
            f"api v0 {prod_id}",
            url=f"https://api.gog.com/products/{prod_id}?expand=downloads,expanded_dlcs,description,screenshots,videos,related_products,changelog&locale=en-US",
            path=self.storage_path / f"raw/prod_v0/{prod_id}_v0.json",
            caching=self.config.get("CACHE_PRODUCT_V0", CACHE_NONE),
            expect_404=True
        )

    async def fetch_product_v2(self, prod_id):
        return await self.get_json_cached(
            f"api v2 {prod_id}",
            url=f"https://api.gog.com/v2/games/{prod_id}?locale=en-US",
            path=self.storage_path / f"raw/prod_v2/{prod_id}_v2.json",
            caching=self.config.get("CACHE_PRODUCT_V2", CACHE_NONE),
            expect_404=True
        )

    async def fetch_builds(self, prod_id, system):
        return await self.get_json_cached(
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
        return await self.get_json_cached(
            f"manifest v1 {mf_name}",
            url=manifest_url,
            path=None,
            caching=CACHE_NONE
        )

    async def fetch_repo_v2(self, repo_url, prod_id, build_id):
        return await self.get_json_cached(
            f"repo v2 {repo_url}",
            url=repo_url,
            path=self.storage_path / f"raw/repo_v2/{prod_id}_{build_id}.json",
            caching=self.config.get("CACHE_REPO_V2", CACHE_NONE),
            decompress=True
        )

    async def fetch_manifest_v2(self, repo_url, manifest_id):
        base_url = repo_url.rsplit("/", 3)[0]
        manifest_url = "/".join((base_url, manifest_id[0:2], manifest_id[2:4], manifest_id))
        return await self.get_json_cached(
            f"manifest v2 {manifest_id}",
            url=manifest_url,
            path=None,
            caching=CACHE_NONE,
            decompress=True
        )

    async def fetch_catalog(self, params, page_num):
        page_params = params.copy()
        cache_id = '_'.join(str(v) for v in page_params.values())
        return await self.get_json_cached(
            f"catalog page {page_num}",
            url="https://catalog.gog.com/v1/catalog",
            params=page_params,
            path=self.storage_path / f"raw/catalog/page_{cache_id}.json",
            caching=self.config.get("CACHE_CATALOG", CACHE_NONE)
        )
