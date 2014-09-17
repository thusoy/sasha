# based on https://jamielinux.com/articles/2013/08/create-an-intermediate-certificate-authority/

ca:
    file.recurse:
        - name: /etc/ca
        - source: salt://ca/files


ca-initial-serial:
     file.managed:
        - name: /etc/ca/serial
        - contents: "1000"
        - replace: False


ca-database:
    file.managed:
        - name: /etc/ca/index.txt


ca-private-dir:
    file.directory:
        - name: /etc/ca/private
        - user: root
        - group: root
        - mode: 700


ca-root-key:
    file.managed:
        - name: /etc/ca/private/root.key
        - contents_pillar: ca.root_key
        - require:
            - file: ca-private-dir
