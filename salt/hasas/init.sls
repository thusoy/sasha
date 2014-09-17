include:
    - nginx

hasas-nginx-site:
    file.managed:
        - name: /etc/nginx/sites-enabled/hasas
        - source: salt://hasas/nginx/hasas


hasas-nginx-key:
    file.managed:
        - name: /etc/nginx/private/hasas.local.key
        - contents_pillar: hasas.private_key
        - user: root
        - group: www-data
        - mode: 640
        - require:
            - file: nginx-private-dir
