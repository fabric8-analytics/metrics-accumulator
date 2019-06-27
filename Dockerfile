FROM registry.centos.org/centos/centos:7

RUN yum install -y epel-release &&\
    yum --setopt=skip_missing_names_on_install=False install -y gcc patch python36-pip httpd httpd-devel python36-devel openssl-devel &&\
    yum clean all

RUN mkdir -p /var/log/prometheus /src && \
    chmod -R g+rwX /var/log/prometheus /src

COPY ./requirements.txt /

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt && rm requirements.txt

ADD src /src
COPY scripts/entrypoint.sh /src/entrypoint.sh
RUN chmod +x /src/entrypoint.sh

ENV prometheus_multiproc_dir /var/log/prometheus

ENTRYPOINT ["/src/entrypoint.sh"]
