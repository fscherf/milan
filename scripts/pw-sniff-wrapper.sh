#!/bin/bash

source env/bin/activate
exec scripts/pw-sniff.py $0 $@
