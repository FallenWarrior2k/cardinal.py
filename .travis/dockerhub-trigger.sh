#!/usr/bin/env bash

echo '$TRAVIS_PULL_REQUEST =' "'$TRAVIS_PULL_REQUEST'"
echo '$TRAVIS_TAG = ' "'$TRAVIS_TAG'"
echo '$TRAVIS_BRANCH = ' "'$TRAVIS_BRANCH'"

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
    -X POST "$DOCKERHUB_BUILD_ENDPOINT"
