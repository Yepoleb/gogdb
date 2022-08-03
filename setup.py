from setuptools import setup, find_packages


requires = [
    # base
    "flask",
    "jinja2",

    # legacy
    "SQLAlchemy",
    "psycopg2",

    # assets
    "webassets",
    "rcssmin",
    "rjsmin",
    "Flask-Assets",

    # util
    "aiohttp",
    "python-dateutil",
    "requests",
    "aiosqlite",
    "bleach"
]

setup(
    name="gogdb",
    version="0.4",
    description="GOG Database",
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Flask",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
    ],
    author="Gabriel Huber",
    author_email="gabriel@yepoleb.at",
    url="https://www.gogdb.org",
    keywords="web flask",
    packages=["gogdb"],
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    entry_points={
        "console_scripts": [
            "gogdb-init = gogdb.scripts.gogdb_init:main",
            "gogdb-add = gogdb.scripts.gogdb_add:main"
        ],
    }
)
