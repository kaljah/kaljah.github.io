#!/bin/bash
# Re-run every Python repro against the CURRENT code. exit 1 = bug still present, 0 = not reproduced.
cd /c/Users/samsung/Desktop/H2/audit/repro
OUT=/c/Users/samsung/Desktop/H2/audit/work/rerun
: > $OUT/results.tsv
for f in $(ls BUG-[0-9][0-9][0-9]*.py | sort); do
  start=$(date +%s)
  timeout 300 python "$f" > "$OUT/${f%.py}.log" 2>&1
  rc=$?
  echo -e "${f}\t${rc}\t$(( $(date +%s) - start ))s" >> $OUT/results.tsv
done
echo DONE >> $OUT/results.tsv
