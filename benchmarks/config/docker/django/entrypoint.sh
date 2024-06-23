#!/bin/bash

if [[ $@ ]]; then  # Pycharm
    eval $@
else
    python manage.py migrate
    python manage.py runserver 0:9037
    # sleep infinity
fi
