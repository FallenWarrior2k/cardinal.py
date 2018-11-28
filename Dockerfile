FROM python:3.5-alpine

WORKDIR /cardinal
COPY . .

RUN apk update \
    && xargs -a docker/apk-rt.txt apk add --no-cache \
    && xargs -a docker/apk-build.txt apk add --no-cache --virtual .build-deps \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir --upgrade --requirement docker/requirements.txt \
    && apk del .build-deps

ENTRYPOINT ["docker/entrypoint.sh"]
