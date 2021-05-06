FROM python:3.8-alpine as builder

RUN apk add --progress \
    build-base \
    git \
    linux-headers \
    postgresql-dev

WORKDIR /wheels
RUN pip wheel psycopg2

WORKDIR /app
COPY . .
RUN pip wheel -w /wheels .

FROM python:3.8-alpine

RUN apk add --no-cache --progress libpq

WORKDIR /cardinal
COPY docker-entrypoint.sh /entrypoint.sh
COPY ./run_cardinal.py ./upgrade_db.py ./
COPY ./src/cardinal/db/migrations ./src/cardinal/db/migrations

COPY --from=builder /wheels /wheels
RUN pip --no-cache-dir install /wheels/*.whl

ENTRYPOINT ["/entrypoint.sh"]
