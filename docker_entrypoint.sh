#!/usr/bin/env bash

# Docker Entrypoint Script
# 
# This script is executed before the python app is run to:
#   - Require HOST_UID and HOST_GID to be set
#   - Update the cassandra user (created by dockerfile) to use 
#     the same user and group ids as the host system
#   - Drop root permissions, then execute all remaining commands
#     passed to the docker run command as the cassandra user
#
# It is required to make sure we can:
#   - Keep the volume files editable by the host system
#       - Note: only a concern on linux, docker desktop for macos 
#               handles the permission issues
#   - Build the docker image without knowing the host user/group
#     ahead of time

set -e

# Only continue if we have both the uid and gid specified
if [[ -z "$HOST_UID" ]]; then
    echo "ERROR: please set HOST_UID" >&2
    exit 1
fi
if [[ -z "$HOST_GID" ]]; then
    echo "ERROR: please set HOST_GID" >&2
    exit 1
fi

# Modify the existing cassandra account to use the host group/user ids
groupmod -o --gid "$HOST_GID" cassandra
usermod --uid "$HOST_UID" cassandra

# Drop privileges and execute next container command, or 'bash' if not specified.
if [[ $# -gt 0 ]]; then
    exec sudo -u cassandra -- "$@"
else
    exec sudo -u cassandra -- bash
fi