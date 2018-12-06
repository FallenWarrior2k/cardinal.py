#!/usr/bin/env bash

# Don't submit Docker builds for PRs
if [[ "$TRAVIS_PULL_REQUEST" != "false" ]]; then
    exit
fi

if [[ -n "$TRAVIS_TAG" ]]; then
    type="Tag"
    source="$TRAVIS_TAG"
else
    type="Branch"
    source="$TRAVIS_BRANCH"
fi

curl -H "Content-Type: application/json" \
    --data "{\"source_type\": \"${type}\", \"source_name\": \"${source}\"}" \
    -X POST "https://registry.hub.docker.com/u/fallenwarrior2k/cardinal.py/trigger/${DOCKERHUB_TOKEN}/"
