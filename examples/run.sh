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

echo "*******************************************************************"
