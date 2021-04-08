# GOG Database

Website that collects data on GOG games.

# Deployment Instructions

All commands need to be run as root. They are specific to Debian Buster, Apache2 and
Gunicorn. If you want to use a different web or app server search for deploying
Flask applications on it.

## Application

Clone the application

    # cd /usr/local/share
    # git clone https://github.com/Yepoleb/gogdb.git
    # cd gogdb

Create system user for the updater

    # adduser --system --home /var/lib/gogdb/ --shell /bin/bash --no-create-home --group --disabled-login --gecos 'GOG DB' gogdb

Create a login token for the updater to use

    # scripts/run.sh token token.json
    # mkdir -p /var/lib/gogdb/storage/secret/
    # mv token.json /var/lib/gogdb/storage/secret/token.json

Set access rights

    # chown -R gogdb:gogdb /var/lib/gogdb/storage/
    # chmod g-rwx,o-rwx -R /var/lib/gogdb/storage/secret/

Copy the example config and set the storage path

    # mkdir /etc/gogdb
    # cp example-production.py /etc/gogdb/config-production.py
    # editor /etc/gogdb/config-production.py

Build assets. Both commands have to be run in a root shell because sudo resets the environment variables

    # export GOGDB_CONFIG=/etc/gogdb/config-production.py
    # scripts/run.sh assets

## Apache2

Apache is used as the webserver to serve static assets and to translate
HTTP/HTTPS into uwsgi requests.

Install Apache2

    # apt install apache2

Copy the config

    # cp conf/apache2/gogdb.conf /etc/apache2/sites-available/

Enable required modules

    # a2enmod proxy
    # a2enmod expires

Enable the site

    # a2ensite gogdb

Restart Apache2

    # systemctl restart apache2

## Gunicorn

Gunicorn is the default application server for GOG DB

Install Gunicorn

    # apt install gunicorn3

Copy the systemd service file

    # cp conf/systemd/gogdb.service /etc/systemd/system/

Start service

    # systemctl daemon-reload
    # systemctl enable gogdb
    # systemctl start gogdb

## Scripts

Scripts insert the data into the database and keep it up to date. They are
also used to build the search index.

Copy the systemd email notify service to receive failed task notifications

    # cp conf/systemd/email-notify@.service /etc/systemd/system/

Copy the systemd services for the updater

    # cp conf/systemd/gogdb-updater.* /etc/systemd/system/
    
Enable the timer

    # systemctl daemon-reload
    # systemctl enable gogdb-updater.timer
    # systemctl start gogdb-updater.timer

Copy the systemd services for the backup

    # cp conf/systemd/gogdb-backup.* /etc/systemd/system/
    
Enable the timer

    # systemctl daemon-reload
    # systemctl enable gogdb-backup.timer
    # systemctl start gogdb-backup.timer

# Database Migrations

See [MIGRATIONS.md](MIGRATIONS.md)

# License

AGPLv3 or later

