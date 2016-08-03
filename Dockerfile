FROM registry.cn-hangzhou.aliyuncs.com/ljchen/floating-ip-worker:latest
MAINTAINER chenleji@wise2c.com
COPY ./ /opt/floating-ip-worker
WORKDIR /opt/floating-ip-worker
ENTRYPOINT ["bash", "start.sh"]