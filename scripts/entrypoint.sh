#!/usr/bin/env bash
#
# entrypoint.sh - single-node DICOM lab (PACS + Modality Worklist on one AE).
#
#   Node       : AET DICOM-VULN-LAB  DICOM :4242  HTTP :8042
#   Mimic AEs  : WORKSTN:11112 CT01:11113 MR01:11114 US01:11115 (C-MOVE targets)
#
# Studies are C-STOREd into the node at boot; worklist items are served from
# /worklists by the Modality Worklists plugin.
#
set -euo pipefail

RECV_DIR=/data/received
mkdir -p "$RECV_DIR"/{WORKSTN,CT01,MR01,US01} /var/lib/orthanc/db

echo "[lab] starting modality/workstation listeners ..."
storescp -aet WORKSTN 11112 --output-directory "$RECV_DIR/WORKSTN" &
storescp -aet CT01    11113 --output-directory "$RECV_DIR/CT01"    &
storescp -aet MR01    11114 --output-directory "$RECV_DIR/MR01"    &
storescp -aet US01    11115 --output-directory "$RECV_DIR/US01"    &

echo "[lab] starting DICOM-VULN-LAB node (PACS + MWL Server) ..."
# Firing default entrypoint script shipped by Orthanc
/docker-entrypoint.sh /tmp/orthanc.json &
NODE_PID=$!

echo "[lab] waiting for DICOM port :4242 ..."
for i in $(seq 1 60); do
  if echoscu -aet SEEDER -aec DICOM-VULN-LAB localhost 4242 >/dev/null 2>&1; then
    echo "[lab] node is up."; break
  fi
  sleep 1
done

if [ ! -f /data/.seeded ]; then
  echo "[lab] loading test studies ..."
  storescu +sd +r -aet SEEDER -aec DICOM-VULN-LAB localhost 4242 /opt/lab/studies \
    && touch /data/.seeded
  echo "[lab] load complete."
else
  echo "[lab] data already seeded, skipping load."
fi

cat <<'BANNER'

  ============================================================
   DICOM-VULN-LAB READY
  ---------------------------------------------------------------------------
   Node        AET=DICOM-VULN-LAB (PACS+MWL Server)   DICOM :4242   UI :8042
   Web UI      http://localhost:8042   (admin/admin)
   Mimic AEs   WORKSTN:11112 CT01:11113 MR01:11114 US01:11115
  ---------------------------------------------------------------------------
     echoscu -aec DICOM-VULN-LAB localhost 4242 -v
     findscu -S -aec DICOM-VULN-LAB localhost 4242 \
             -k QueryRetrieveLevel=STUDY -k PatientName= -k StudyInstanceUID=
     findscu -W -aec DICOM-VULN-LAB localhost 4242 \
             -k PatientName= -k "ScheduledProcedureStepSequence[0].Modality="
  ============================================================

BANNER

wait "$NODE_PID"
