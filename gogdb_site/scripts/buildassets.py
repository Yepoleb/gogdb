import os
import sys

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    bootstrap
    )

from pyramid.scripts.common import parse_vars

import webassets.script


def usage(argv):
    cmd = os.path.basename(argv[0])
    print("usage: %s <config_uri> [var=value]\n"
          "(example: %s development.ini)" % (cmd, cmd))
    sys.exit(1)


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    setup_logging(config_uri)

    app_env = bootstrap(config_uri)
    assets_env = app_env["request"].webassets_env
    webassets.script.main(["build"], assets_env)
