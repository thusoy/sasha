nginx:
    pkgrepo.managed:
        - ppa: nginx/stable

    pkg.installed:
        - require:
            - pkgrepo: nginx

    file.managed:
        - name: /etc/nginx/nginx.conf
        - source: salt://nginx/nginx.conf
        - mode: 644
        - user: root
        - group: www-data
        - require:
            - pkg: nginx

    service.running:
        - watch:
            - file: nginx


# Disable default site
nginx-default-site:
    file.absent:
        - name: /etc/nginx/sites-enabled/default
        - require:
            - pkg: nginx


nginx-private-dir:
    file.directory:
        - name: /etc/nginx/private
        - user: root
        - group: www-data
        - mode: 750
        - require:
            - pkg: nginx
