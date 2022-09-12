import re
from dataclasses import dataclass
import datetime

import gogdb.core.model as model


@dataclass
class Version:
    gog: str = None
    number: str = None
    doted: str = None
    date: str = None
    issue: str = None

    def __bool__(self):
        return bool(self.number or self.doted or self.date)

    def __str__(self):
        return str(self.number or self.doted or self.date)

@dataclass
class IssueEntry:
    id: int
    title: str
    os: str
    type: str
    version: str
    interpreted: str
    reason: str

def parse_version(version_str):
    if not version_str:
        return Version(issue="empty")
    version_str = version_str.lower()
    version = Version()
    # Examples: (gog-7), (gog-2a), gog-3
    gog_match = re.search(r"\s*\(?gog-(\d+)\w?(?:\)|\s+|$)", version_str)
    if gog_match:
        version.gog = gog_match.group(1)
        version_str = version_str[:gog_match.start(0)] + version_str[gog_match.end(0):]
        if not version_str:
            version.issue = "onlygog"
            return version
    # Example: 2022-08-17
    date_match = re.search(r"(\d{4})[-_/\.](\d{2})[-_/\.](\d{2})", version_str)
    if date_match:
        version.date = "-".join((date_match.group(1), date_match.group(2), date_match.group(3)))
        if not "-" in date_match.group(0):
            version.issue = "date"
        return version
    # Example: 17-08-2022
    # Parses cursed mm/dd/yyyy incorrectly, but should work as long as it's used consistently
    stupid_date_match = re.search(r"(\d{2})[-_/\.](\d{2})[-_/\.](\d{4})", version_str)
    if stupid_date_match:
        version.date = "-".join((
            stupid_date_match.group(3), stupid_date_match.group(2), stupid_date_match.group(1)
        ))
        version.issue = "date"
        return version
    # Examples: 1.2.3, 2019.03.24, 1.1.1.4.6
    doted_match = re.search(r"(\d+\.\d+(?:\.\d+)*)(?:\w(?:\s|$))?", version_str)
    if doted_match:
        doted_str = doted_match.group(1)
        doted_norm = ".".join((str(int(n)) for n in doted_str.split(".")))
        version.doted = doted_norm
        if doted_str != doted_norm:
            version.issue = "doted"
        return version
    # Examples: 1843, v329, r78b, patch 2 hotfix, build 9, 142 lang update
    number_match = re.findall(r"(\d+)", version_str)
    if len(number_match) == 1:
        version.number = number_match[0]
        return version

    if not version:
        version.issue = "unparsable"
    return version

def compare_version(a, b):
    if a.doted is not None and a.doted == b.doted:
        return True
    elif a.date is not None and a.date == b.date:
        return True
    elif a.number is not None and a.number == b.number:
        return True
    else:
        if a.doted:
            a_fuzzy = a.doted.replace(".", "")
        elif a.number:
            a_fuzzy = a.number
        else:
            return False
        if b.doted:
            b_fuzzy = b.doted.replace(".", "")
        elif b.number:
            b_fuzzy = b.number
        else:
            return False

        if a_fuzzy == b_fuzzy:
            a.issue = "fuzzy"
            b.issue = "fuzzy"
            return True
        else:
            return False


class VersionsProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.mismatches = []
        self.issues = []
        self.all = set()

    async def prepare(self):
        pass

    async def process(self, data):
        prod = data.product
        if prod is None:
            return

        for os_name in ["windows", "osx"]:
            os_builds = [
                build for build in prod.builds
                if (
                    build.os == os_name and
                    (build.version is None or "beta" not in build.version.lower())
                )
            ]
            os_dls = [dl for dl in prod.dl_installer if dl.os == os_name and dl.language.code == "en"]
            if os_builds and os_dls:
                last_build_vers = os_builds[-1].version
                last_dl_vers = os_dls[-1].version
                last_build_parsed = parse_version(last_build_vers)
                last_dl_parsed = parse_version(last_dl_vers)
                if last_build_parsed and last_dl_parsed and not compare_version(last_build_parsed, last_dl_parsed):
                    self.mismatches.append(model.Mismatch(
                        id = prod.id,
                        title = prod.title,
                        os = os_name,
                        version_build = last_build_vers,
                        version_dl = last_dl_vers,
                        build_published = os_builds[-1].date_published
                    ))

                for version_string, version_parsed, version_type in (
                        (last_build_vers, last_build_parsed, "build"),
                        (last_dl_vers, last_dl_parsed, "dl")):
                    if version_parsed.issue:
                        self.issues.append(IssueEntry(
                            id = prod.id,
                            title = prod.title,
                            os = os_name,
                            type = version_type,
                            version = version_string,
                            interpreted = str(version_parsed),
                            reason = version_parsed.issue
                        ))


    async def finish(self):
        self.mismatches.sort(key=lambda m: m.build_published, reverse=True)
        await self.db.versions.save(self.mismatches)
