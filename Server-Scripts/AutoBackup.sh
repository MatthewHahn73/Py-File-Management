#!/bin/bash

SRCDIR="/home/$USER/Desktop/Files"
DESTDIR="/home/$USER/Desktop/Backups/"
DATE=$(date +"%d-%b-%Y")
FILENAME=Server-Backup-$DATE.tar.gz
mkdir -p $DESTDIR
cd $DESTDIR
tar -cvzf $DESTDIR$FILENAME --absolute-names $SRCDIR 