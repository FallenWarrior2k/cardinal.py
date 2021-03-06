FROM python:3.8-alpine as builder

RUN apk add \
    build-base \
    git \
    linux-headers \
    postgresql-dev

WORKDIR /app
COPY . .
RUN pip wheel -w /wheels .[pgsql]

FROM python:3.8-alpine

RUN apk add --no-cache libpq

WORKDIR /cardinal
COPY docker-entrypoint.sh /entrypoint.sh
COPY ./run_cardinal.py ./upgrade_db.py ./
COPY ./src/cardinal/db/migrations ./src/cardinal/db/migrations

COPY --from=builder /wheels /wheels
RUN pip --no-cache-dir install /wheels/*.whl

ENTRYPOINT ["/entrypoint.sh"]
