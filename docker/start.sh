#!/bin/bash

echo "Starting services..."
echo "PATH=${PATH}"
mkdir -p ~/pigleg/logs/
cd /webapps/piglegsurgery/piglegsurgeryweb
if [ -f /.dockerenv ]; then
    echo "I'm inside docker";
    sudo service redis-server start |& \
        tee >(rotatelogs -n 1 ~/pigleg/logs/redis_{$DOCKERLOGNAME}_log.txt 1M) | \
        tee >(rotatelogs -n 3 ~/pigleg/logs/redis_{$DOCKERLOGNAME}_log.txt.bck 1M)
    echo "  Redis started"
else
    echo "Not running in docker, redis should be already running.";
fi
conda run -n piglegsurgery --no-capture-output python manage.py qcluster |& \
    tee >(rotatelogs -n 1 ~/pigleg/logs/qcluster_{$DOCKERLOGNAME}_log.txt 1M) | \
    tee >(rotatelogs -n 3 ~/pigleg/logs/qcluster_{$DOCKERLOGNAME}_log.txt.bck 1M) &
echo "  QCluster started"
conda run -n piglegsurgery --no-capture-output python manage.py runserver 0:8000 |& \
    tee >(rotatelogs -n 1 ~/pigleg/logs/runserver_{$DOCKERLOGNAME}_log.txt 1M) | \
    tee >(rotatelogs -n 3 ~/pigleg/logs/runserver_{$DOCKERLOGNAME}_log.txt.bck 1M) &
echo "  Django (debug) webserver started"

# TODO production run
#gunicorn --log-level debug piglegsurgeryweb.wsgi:application --bind 0:8000 --timeout 1800 --workers 5 |& \
#    tee >(rotatelogs -n 3 /webapps/piglegsurgery/piglegsurgeryweb/log/gunicorn_log.txt.bck 1k) | tee  >(rotatelogs -n 1 /webapps/piglegsurgery/piglegsurgeryweb/log/gunicorn_log.txt 1M)
echo "Services started"
