#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Run in an empty build directory with the path to a verified FFmpeg source tree.
set -eu

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 /path/to/ffmpeg-source [toolchain options]" >&2
    exit 2
fi

source_dir=$(cd "$1" && pwd)
shift
for option in "$@"; do
    case "$option" in
        --prefix=*|--arch=*|--target-os=*|--cc=*|--cross-prefix=*|--enable-cross-compile|--install-name-dir=*) ;;
        *) echo "Unsupported toolchain option: $option" >&2; exit 2 ;;
    esac
done

exec "$source_dir/configure" "$@" \
    --disable-autodetect --disable-everything --disable-gpl --disable-version3 --disable-nonfree \
    --disable-static --enable-shared --disable-doc --disable-debug --disable-asm \
    --disable-ffplay --disable-ffprobe --disable-avdevice --disable-swresample \
    --enable-ffmpeg --enable-network \
    --enable-protocol=http,tcp,pipe --enable-demuxer=flv --enable-parser=h264 \
    --enable-decoder=h264 --enable-encoder=mjpeg --enable-muxer=image2pipe \
    --enable-filter=fps,format,scale,transpose,hflip,vflip
