#!/bin/bash
set -euo pipefail
install -d -m 0755 \
  /var/www/trust-ci-acme/.well-known/acme-challenge \
  /var/www/trust-ci-empty
cat >/etc/apache2/sites-available/trust-ci.conf <<'APACHE'
<VirtualHost *:80>
    ServerName trust-ci.ii-tonya.ru

    DocumentRoot /var/www/trust-ci-acme

    <Directory "/var/www/trust-ci-acme">
        Options -Indexes
        AllowOverride None
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/trust-ci-error.log
    CustomLog ${APACHE_LOG_DIR}/trust-ci-access.log combined
</VirtualHost>
APACHE
a2ensite trust-ci.conf
apache2ctl configtest
systemctl reload apache2
