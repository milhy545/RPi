#!/bin/bash
ROOTFS_DIR="rootfs"

if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Složka $ROOTFS_DIR neexistuje."
    exit 1
fi

echo "Odpojuji systémové soubory..."
sudo umount $ROOTFS_DIR/proc
sudo umount $ROOTFS_DIR/sys
sudo umount $ROOTFS_DIR/dev/pts
sudo umount $ROOTFS_DIR/dev
sudo umount $ROOTFS_DIR/run

echo "Systémy byly odpojeny."
