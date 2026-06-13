#!/bin/bash
ROOTFS_DIR="rootfs"

if [ ! -d "$ROOTFS_DIR" ]; then
    echo "Složka $ROOTFS_DIR neexistuje."
    exit 1
fi

echo "Kopíruji qemu-arm-static do rootfs..."
sudo cp /usr/bin/qemu-arm-static $ROOTFS_DIR/usr/bin/

echo "Připojuji systémové soubory..."
sudo mount -t proc /proc $ROOTFS_DIR/proc
sudo mount -t sysfs /sys $ROOTFS_DIR/sys
sudo mount -o bind /dev $ROOTFS_DIR/dev
sudo mount -o bind /dev/pts $ROOTFS_DIR/dev/pts
sudo mount -o bind /run $ROOTFS_DIR/run

# Povolení DNS v chrootu
sudo cp /etc/resolv.conf $ROOTFS_DIR/etc/resolv.conf

echo "Systémy byly úspěšně připojeny."
echo "Pro vstup zadejte: sudo chroot $ROOTFS_DIR /bin/bash"
