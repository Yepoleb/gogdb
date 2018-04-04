# GOG Database

Website that collects data on GOG games.

# Deployment Instructions

Commands are prefixed with `$` or `#` depending if they can be run as a regular
user or must be run as root. They are specific to Debian/Ubuntu, Apache2 and
uWSGI. If you want to use a different web or app server search for deploying
Flask applications.

## Application

Install git and Python virtualenv

    # apt install git python3-venv

Install gcc and python headers if you want faster assets building (optional)

    # apt install gcc python3-dev

Clone the application

    # git clone https://github.com/Yepoleb/gogdb.git
    $ cd gogdb

Create virtual environment

    # python3 -m venv venv

Install application into virtualenv

    # venv/bin/pip install setuptools wheel --upgrade
    # venv/bin/pip install -r requirements.txt

Install PostgreSQL and create database

    # apt install postgres
    # sudo -u postgres psql
    postgres=# CREATE USER gogdb WITH PASSWORD '12345678';
    postgres=# CREATE DATABASE gogdb WITH OWNER = gogdb;
    postgres=# \q

Copy the example config and set database password

    # cp example-production.py production.py
    # editor production.py

Set up environment

    $ export FLASK_APP=gogdb
    $ export GOGDB_CONFIG=../config-development.py

Initialize database

    $ venv/bin/gogdb-init

Build assets

    # venv/bin/flask assets build

## Apache2

Apache is used as the webserver to serve static assets and to translate
HTTP/HTTPS into uwsgi requests.

Install Apache2

    # apt install apache2

Copy the config

    # cp doc/apache2/gogdb.conf /etc/apache2/conf-available/

Enable required modules

    # a2enmod proxy_uwsgi
    # a2enmod expires

Enable config

    # a2enconf gogdb

Restart Apache2

    # systemctl restart apache2

## uWSGI

uWSGI provides the environment the application needs to run.

Install uWSGI, its Python 3 plugin and the Apache module

    # apt install uwsgi uwsgi-plugin-python3 libapache2-mod-proxy-uwsgi

Copy the config

    # cp doc/uwsgi/gogdb.ini /etc/uwsgi/apps-available/

Enable the config

    # ln -s /etc/uwsgi/apps-available/gogdb.ini /etc/uwsgi/apps-enabled/gogdb.ini

Restart uWSGI

    # systemctl restart uwsgi

## Scripts

Scripts insert the data into the database and keep it up to date. They are
also used to build the search index.

Create the log directory and make it writable

    # mkdir -p /var/log/gogdb
    # chown www-data:www-data /var/log/gogdb

Change the `CONFIG_FILE` variable inside `/scripts/update.sh` to the
`production.ini` or symlink it to `development.ini`.

    # edit scripts/update.sh

or

    # ln -s production.ini development.ini

Copy the cron and logrotate configs

    # cp doc/cron/gogdb /etc/cron.d/
    # cp doc/logrotate/gogdb /etc/logrotate.d/

# Database Migrations

## 18fc238 to cec5ebc

This commit removes the `searchindex` table and adds a product column instead.

    ALTER TABLE products ADD COLUMN title_norm character varying(120);
    UPDATE products SET title_norm = searchindex.title_norm
        FROM searchindex WHERE id = searchindex.prod_id;
    ALTER TABLE products ALTER COLUMN title_norm SET NOT NULL;
    DROP TABLE searchindex;

## 728681b to a2c8a1a

This commit adds deleted columns to files and downloads. Also run the
`initialize-db` script to create the `changerecords` table.

    ALTER TABLE files ADD COLUMN deleted BOOLEAN;
    ALTER TABLE downloads ADD COLUMN deleted BOOLEAN;
    UPDATE files SET deleted=FALSE;
    UPDATE downloads SET deleted=FALSE;
    ALTER TABLE files ALTER COLUMN deleted SET NOT NULL;
    ALTER TABLE downloads ALTER COLUMN deleted SET NOT NULL;


# License

AGPLv3 or later

