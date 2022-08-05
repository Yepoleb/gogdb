from setuptools import setup, find_packages


requires = [
    # base
    "quart",
    "jinja2",

    # legacy
    "SQLAlchemy",
    "psycopg2",

    # charts
    "pygal",
    "lxml",

    # storage
    "aiosqlite",
    "aiofiles",

    # util
    "aiohttp",
    "python-dateutil",
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
    install_requires=requires
)
