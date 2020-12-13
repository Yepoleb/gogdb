import json
import datetime
import copy

import gogdb.core.model as model
from gogdb.core.normalization import normalize_system


def normalize_bitness(bitness_list):
    if not bitness_list:
        return "any"
    elif bitness_list == ["32"] or ["64"]:
        return bitness_list[0]
    else:
        return "other"

def int_or_none(value):
    if value is None:
        return None
    else:
        return int(value)


class FallbackDict:
    def __init__(self, data, defaults):
        self.data = data
        self.defaults = defaults

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            return copy.copy(self.defaults[key])


DEPOT_V1_DEFAULTS = {
    "gameIDs": [],
    "languages": ["Neutral"],
    #"manifest": ,
    "size": "0",
    "systems": ["Windows"],
}

def load_depot_v1(data):
    source = FallbackDict(data, DEPOT_V1_DEFAULTS)
    return model.DepotV1(
        languages = source["languages"],
        size = int(source["size"]),
        game_ids = [int(x) for x in source["gameIDs"]],
        system = normalize_system(source["systems"][0]),
        manifest = source["manifest"]
    )

REDIST_V1_DEFAULTS = {
    "argument": None,
    "executable": None,
    #"redist": ,
    "size": "0",
    "targetDir": None
}

def load_redist_v1(data):
    source = FallbackDict(data, REDIST_V1_DEFAULTS)
    return model.RedistV1(
        redist = source["redist"],
        executable = source["executable"],
        argument = source["argument"],
        target_dir = source["targetDir"]
    )

SUPPORT_COMMAND_V1_DEFAULTS = {
    "argument": "",
    #"executable": ,
    "gameID": None,
    "languages": ["Neutral"],
    "systems": ["Windows"]
}

def load_support_command_v1(data):
    source = FallbackDict(data, SUPPORT_COMMAND_V1_DEFAULTS)
    return model.SupportCommandV1(
        language = source["languages"][0],
        executable = source["executable"],
        product_id = int_or_none(source["gameID"]),
        system = normalize_system(source["systems"][0])
    )

REPOSITORYPRODUCT_V1_DEFAULTS = {
    "dependencies": [None],
    #"gameID": ,
    #"name": {"en": "Fallout 2"},
    "standalone": False
}

def load_repositoryproduct_v1(data):
    source = FallbackDict(data, REPOSITORYPRODUCT_V1_DEFAULTS)
    return model.RepositoryProductV1(
        dependency = int_or_none((source["dependencies"] or [None])[0]),
        product_id = int(source["gameID"]),
        name = source["name"]["en"],
        standalone = source["standalone"]
    )

REPOSITORY_V1_DEFAULTS = {
    "depots": [],
    "gameIDs": [],
    #"installDirectory": "Fallout 2",
    #"projectName": "Fallout 2",
    "rootGameID": None,
    "support_commands": [],
    "timestamp": None
}

def load_repository_v1(data):
    source = FallbackDict(data["product"], REPOSITORY_V1_DEFAULTS)
    return model.RepositoryV1(
        timestamp = source["timestamp"],
        depots = [load_depot_v1(x) for x in source["depots"] if "manifest" in x],
        redists = [load_redist_v1(x) for x in source["depots"] if "manifest" not in x],
        support_commands = [load_support_command_v1(x) for x in source["support_commands"]],
        install_directory = source["installDirectory"],
        root_game_id = int_or_none(source["rootGameID"]),
        products = [load_repositoryproduct_v1(x) for x in source["gameIDs"]],
        name = source["projectName"]
    )


# Manifest V1
# ===========

DEPOTITEM_V1_DEFAULTS = {
    "hash": None,
    "offset": 0,
    #"path": ,
    "size": 0,
    "url": None,
    "symlinkType": None,
    "target": None,
    "executable": False,
    "hidden": False,
    "support": False,
    "directory": False
}

def load_depotlink_v1(source):
    return model.DepotLinkV1(
        path = source["path"],
        target = source["target"],
        link_type = source["symlinkType"]
    )

def depotfile_v1_flags(source):
    return [
        flagname for flagname in ["executable", "hidden", "support"]
        if source[flagname]
    ]

def load_depotfile_v1(source):
    return model.DepotFileV1(
        path = source["path"],
        size = source["size"],
        checksum = source["hash"],
        url = source["url"],
        offset = source["offset"],
        flags = depotfile_v1_flags(source)
    )

def load_depotdirectory_v1(source):
    return model.DepotDirectoryV1(
        path = source["path"],
        flags = depotfile_v1_flags(source)
    )

def load_manifest_v1(data):
    manifest = model.DepotManifestV1(
        name = data["depot"]["name"],
        files = [],
        directories = [],
        links = []
    )
    for item in data["depot"]["files"]:
        item_source = FallbackDict(item, DEPOTITEM_V1_DEFAULTS)
        if item_source["symlinkType"] is not None:
            manifest.links.append(load_depotlink_v1(item_source))
        elif item_source["directory"]:
            manifest.directories.append(load_depotdirectory_v1(item_source))
        else:
            manifest.files.append(load_depotfile_v1(item_source))
    return manifest


# Repository V2
# =============

def load_cloudsave_v2(data):
    # No defaults
    return model.CloudSaveV2(
        location = data["location"],
        name = data["name"]
    )

DEPOT_V2_DEFAULTS = {
    "compressedSize": 0,
    "isGogDepot": False,
    "languages": ["en"],
    #"manifest": ,
    "osBitness": [],
    "productId": None,
    "size": 0
}

def load_depot_v2(data):
    source = FallbackDict(data, DEPOT_V2_DEFAULTS)
    return model.DepotV2(
        compressed_size = source["compressedSize"],
        size = source["size"],
        languages = source["languages"],
        manifest_id = source["manifest"],
        product_id = int_or_none(source["productId"]),
        is_gog_depot = source["isGogDepot"],
        # Possible values: ["32"], ["64"], ["!32", "!64"]
        # The third option contains just the support files without any of the
        # Game data
        os_bitness = normalize_bitness(source["osBitness"])
    )

REPOSITORYPRODUCT_V2_DEFAULTS = {
    #"name": ,
    #"productId": ,
    "script": None,
    "temp_arguments": "",
    "temp_executable": ""
}

def load_repositoryproduct_v2(data):
    source = FallbackDict(data, REPOSITORYPRODUCT_V2_DEFAULTS)
    return model.RepositoryProductV2(
        name = source["name"],
        product_id = int(source["productId"]),
        script = source["script"],
        temp_arguments = source["temp_arguments"],
        temp_executable = source["temp_executable"],
    )

REPOSITORY_V2_DEFAULTS = {
  "baseProductId": None,
  "buildId": None,
  "clientId": None,
  "clientSecret": None,
  "cloudSaves": [],
  "dependencies": [],
  "depots": [],
  #"installDirectory": ,
  #"offlineDepot": ,
  #"platform": ,
  "products": [],
  "scriptInterpreter": False,
  "tags": [],
  "version": 2
}

def load_repository_v2(data):
    source = FallbackDict(data, REPOSITORY_V2_DEFAULTS)
    return model.RepositoryV2(
        base_product_id = int_or_none(source["baseProductId"]),
        client_id = source["clientId"],
        client_secret = source["clientSecret"],
        cloudsaves = [load_cloudsave_v2(x) for x in source["cloudSaves"]],
        dependencies = source["dependencies"],
        depots = [load_depot_v2(x) for x in source["depots"]],
        install_directory = source["installDirectory"],
        offline_depot = load_depot_v2(source["offlineDepot"]),
        platform = normalize_system(source["platform"]),
        products = [load_repositoryproduct_v2(x) for x in source["products"]],
        script_interpreter = source["scriptInterpreter"],
        tags = source["tags"]
    )


# Manifest V2
# ===========

def load_depotchunk_v2(data):
    return model.DepotChunkV2(
        compressed_md5 = data["compressedMd5"],
        compressed_size = data["compressedSize"],
        md5 = data["md5"],
        size = data["size"]
    )

DEPOTFILE_V1_DEFAULTS = {
    #"chunks": ,
    "sfcRef": {"offset": None, "size": None},
    "flags": [],
    "path": None,
    "md5": None,
    "sha256": None
}

def load_depotfile_v2(data):
    source = FallbackDict(data, DEPOTFILE_V1_DEFAULTS)
    return model.DepotFileV2(
        chunks = [load_depotchunk_v2(x) for x in source["chunks"]],
        sfc_offset = source["sfcRef"]["offset"],
        sfc_size = source["sfcRef"]["size"],
        flags = source["flags"],
        path = source["path"],
        md5 = source["md5"],
        sha256 = source["sha256"]
    )

def load_depotdirectory_v2(data):
    return model.DepotDirectoryV2(
        path = data["path"]
    )

def load_depotlink_v2(data):
    return model.DepotLinkV2(
        path = data["path"],
        target = data["target"]
    )

def load_manifest_v2(data):
    manifest = model.DepotManifestV2(
        files = [],
        directories = [],
        links = []
    )
    for item in data["depot"]["items"]:
        if item["type"] == "DepotDirectory":
            manifest.directories.append(load_depotdirectory_v2(item))
        elif item["type"] == "DepotLink":
            manifest.links.append(load_depotlink_v2(item))
        else:
            manifest.files.append(load_depotfile_v2(item))
    if "smallFilesContainer" in data["depot"]:
        manifest.small_files_container = load_depotfile_v2(data["depot"]["smallFilesContainer"])
    return manifest

