#!/bin/sh
# Builds tu01_file next to this script, statically linked against TestU01.
# TESTU01_PREFIX: root holding usr/include/testu01 and usr/lib/<arch>/libtestu01*.a
#   Docker/system install (apt install libtestu01-0-dev): default "/"
#   WSL without sudo (apt-get download + dpkg -x):        "$HOME/.local/testu01"
set -e
cd "$(dirname "$0")"
PREFIX="${TESTU01_PREFIX:-/}"
LIBDIR="$(dirname "$(find "$PREFIX/usr/lib" -name libtestu01.a | head -1)")"
gcc -O2 -o tu01_file tu01_file.c \
    -I"$PREFIX/usr/include" -I"$PREFIX/usr/include/$(gcc -dumpmachine)" \
    "$LIBDIR/libtestu01.a" "$LIBDIR/libtestu01probdist.a" "$LIBDIR/libtestu01mylib.a" -lm
echo "built $(pwd)/tu01_file"
