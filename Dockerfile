# DICOM-VULN-LAB: Vulnerable DICOM Lab Setup using Orthanc's PACS server
FROM orthancteam/orthanc:24.10.1

USER root

# DCMTK provides the client tools (echoscu/findscu/getscu/movescu/storescu),
# the storescp listeners used as mimic modality/workstation AEs, and the
# storescu that seeds the node at boot.
RUN apt-get update && apt-get install -y --no-install-recommends \
        dcmtk bash \
    && rm -rf /var/lib/apt/lists/*

# Pre-baked synthetic data:
#   studies/  -> studies, C-STOREd into the node at boot
#   worklists/ -> *.wl files, served by the Modality Worklists plugin
COPY testdata/studies         /opt/lab/studies
COPY testdata/worklists        /worklists
COPY scripts/entrypoint.sh /opt/lab/entrypoint.sh
COPY config/orthanc.json   /etc/orthanc/orthanc.json
RUN chmod +x /opt/lab/entrypoint.sh

# 4242 DICOM (PACS+MWL) | 8042 HTTP/REST + web UI | 11112-11115 mimic AE listeners
EXPOSE 4242 8042 11112 11113 11114 11115

ENTRYPOINT ["/opt/lab/entrypoint.sh"]
