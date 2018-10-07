#!/bin/bash

echo "*******************************************************************"
echo "RUNNING ON:"
python -V
echo ""

python connect.py
python crud.py
python transaction.py
python lease.py
python watch.py

python etcdb/basic.py
python etcdb/index.py
python etcdb/tut1.py
python etcdb/tut2.py
python etcdb/tut3.py
python etcdb/tut3.py  # yes, run a 2nd time!

echo "*******************************************************************"
