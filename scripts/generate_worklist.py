#!/usr/bin/env python3
"""
generate_worklist.py - Generate Modality Worklist (.wl) files for Orthanc.

The Orthanc ModalityWorklists plugin serves worklist items from a directory of
DICOM files (conventionally *.wl). Each file is a DICOM dataset carrying the
MWL attributes: top-level patient/request identifiers plus a
ScheduledProcedureStepSequence holding the scheduled-step attributes.

All data is synthetic.
"""

import argparse
import datetime
import os
import random

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

ORG_ROOT = "1.2.826.0.1.3680043.8.498"

FIRST = ["ALEX", "SAM", "JORDAN", "TAYLOR", "MORGAN", "CASEY", "RILEY"]
LAST = ["TESTER", "SAMPLE", "DEMO", "FAKELY", "PLACEHOLDER", "PROBER"]
MODALITIES = ["CT", "MR", "US", "CR", "DX"]
# scheduled station AE titles = the "modality machines" in the lab
STATIONS = {"CT": "CT01", "MR": "MR01", "US": "US01", "CR": "CR01", "DX": "DX01"}
PROC_DESC = {
    "CT": "CT HEAD WO CONTRAST", "MR": "MRI BRAIN WO",
    "US": "US ABDOMEN COMPLETE", "CR": "XR CHEST 2 VIEWS",
    "DX": "DX CHEST PA LAT",
}


def build_worklist_item(rng, within_days):
    modality = rng.choice(MODALITIES)
    delta = rng.randint(0, within_days)
    d = datetime.date.today() - datetime.timedelta(days=delta)
    sched_date = d.strftime("%Y%m%d")
    sched_time = f"{rng.randint(7,17):02d}{rng.randint(0,59):02d}00"

    fm = FileMetaDataset()
    fm.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.31"   # MWL FIND
    fm.MediaStorageSOPInstanceUID = generate_uid(prefix=ORG_ROOT + ".")
    fm.TransferSyntaxUID = ExplicitVRLittleEndian
    fm.ImplementationClassUID = generate_uid(prefix=ORG_ROOT + ".")

    ds = Dataset()
    ds.file_meta = fm
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # --- top-level (patient identification / request) ---
    ds.PatientName = f"{rng.choice(LAST)}^{rng.choice(FIRST)}"
    ds.PatientID = f"TEST{rng.randint(1000,1999):04d}"
    ds.PatientBirthDate = f"{rng.randint(1945,2010):04d}0101"
    ds.PatientSex = rng.choice(["M", "F", "O"])
    ds.AccessionNumber = f"ACC{rng.randint(100000,999999)}"
    ds.ReferringPhysicianName = "REFERRING^DOCTOR^TEST"
    ds.StudyInstanceUID = generate_uid(prefix=ORG_ROOT + ".")
    ds.RequestedProcedureID = f"RP{rng.randint(1000,9999)}"
    ds.RequestedProcedureDescription = PROC_DESC[modality]

    # --- Scheduled Procedure Step Sequence (nested) ---
    sps = Dataset()
    sps.Modality = modality
    sps.ScheduledStationAETitle = STATIONS[modality]
    sps.ScheduledProcedureStepStartDate = sched_date
    sps.ScheduledProcedureStepStartTime = sched_time
    sps.ScheduledPerformingPhysicianName = "PERFORMING^DOCTOR^TEST"
    sps.ScheduledProcedureStepDescription = PROC_DESC[modality]
    sps.ScheduledProcedureStepID = f"SPS{rng.randint(1000,9999)}"
    sps.ScheduledStationName = f"{STATIONS[modality]}_ROOM"
    ds.ScheduledProcedureStepSequence = [sps]

    return ds, modality


def main():
    p = argparse.ArgumentParser(description="Generate MWL .wl files.")
    p.add_argument("--outdir", default="/worklists")
    p.add_argument("--count", type=int, default=12)
    p.add_argument("--within-days", type=int, default=30)
    p.add_argument("--seed", type=int, default=4242)
    args = p.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(args.outdir, exist_ok=True)
    for i in range(args.count):
        ds, modality = build_worklist_item(rng, args.within_days)
        path = os.path.join(args.outdir, f"wl{i+1:03d}_{modality}.wl")
        ds.save_as(path, enforce_file_format=True)
    print(f"[+] Generated {args.count} worklist items under {args.outdir}")


if __name__ == "__main__":
    main()
