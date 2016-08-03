#!/usr/bin/env bash

gunicorn -b unix:///var/run/wise2c_fip_worker.sock main:app