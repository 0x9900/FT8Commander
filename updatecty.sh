#!/bin/bash
TEMPCTY="bigcty/cty.tmp"
TARGET="bigcty/cty.csv"

curl -s -o ${TEMPCTY} https://www.country-files.com/cty/cty.csv

cmp -s ${TEMPCTY} ${TARGET}

if [[ $? == 0 ]]; then
    echo "No changes"
    rm -f ${TEMPCTY}
else
    echo "Installing the new version of cty.csv"
    mv ${TEMPCTY} ${TARGET}
fi
