#!/usr/bin/env python3
"""
generate_testdata.py - Synthetic DICOM study generator for a test PACS.

Produces a set of fake patients, each with one or more studies across several
modalities (CT, MR, CR, US, DX), each study with series and image instances
carrying real (small) pixel data, written as DICOM Part 10 files.

All data is synthetic. Names/IDs are obviously fake. Nothing here is PHI.

Output: <outdir>/<PatientID>/<StudyUID>/<SeriesUID>/<InstanceUID>.dcm
"""

import argparse
import datetime
import os
import random

import numpy as np
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import (ExplicitVRLittleEndian, generate_uid,
                         CTImageStorage, MRImageStorage,
                         ComputedRadiographyImageStorage,
                         UltrasoundImageStorage,
                         DigitalXRayImageStorageForPresentation)

ORG_ROOT = "1.2.826.0.1.3680043.8.498"   # example org root for generated UIDs

# modality -> (Storage SOP Class UID, samples_per_pixel, rows, cols, is_rgb)
MODALITIES = {
    "CT": (CTImageStorage, 1, 128, 128, False),
    "MR": (MRImageStorage, 1, 128, 128, False),
    "CR": (ComputedRadiographyImageStorage, 1, 160, 128, False),
    "DX": (DigitalXRayImageStorageForPresentation, 1, 160, 128, False),
    "US": (UltrasoundImageStorage, 3, 120, 160, True),
}

FIRST = ["ALEX", "SAM", "JORDAN", "TAYLOR", "MORGAN", "CASEY", "RILEY",
         "JAMIE", "AVERY", "QUINN", "DREW", "PARKER"]
LAST = ["TESTER", "SAMPLE", "DEMO", "FAKELY", "PLACEHOLDER", "NULLSON",
        "EXAMPLE", "MOCKINGLY", "SYNTHIA", "PROBER"]

STUDY_DESC = {
    "CT": ["CT HEAD WO CONTRAST", "CT CHEST W CONTRAST", "CT ABDOMEN PELVIS"],
    "MR": ["MRI BRAIN WO", "MRI LUMBAR SPINE", "MRI KNEE RIGHT"],
    "CR": ["XR CHEST 2 VIEWS", "XR HAND LEFT"],
    "DX": ["DX CHEST PA LAT", "DX FOOT AP"],
    "US": ["US ABDOMEN COMPLETE", "US ECHO CARDIAC"],
}


def make_pixels(rows, cols, is_rgb, seed):
    rng = np.random.default_rng(seed)
    if is_rgb:
        arr = rng.integers(0, 255, size=(rows, cols, 3), dtype=np.uint8)
        # a soft gradient so it isn't pure noise
        yy = np.linspace(0, 200, rows, dtype=np.uint8)[:, None, None]
        arr = np.clip(arr // 2 + yy, 0, 255).astype(np.uint8)
        return arr
    arr = rng.integers(0, 1200, size=(rows, cols), dtype=np.uint16)
    xx = np.linspace(0, 800, cols, dtype=np.uint16)[None, :]
    arr = np.clip(arr // 2 + xx, 0, 4095).astype(np.uint16)
    return arr


def build_instance(pt, study, series, modality, inst_num, seed):
    sop_uid, spp, rows, cols, is_rgb = MODALITIES[modality]

    fm = FileMetaDataset()
    fm.MediaStorageSOPClassUID = sop_uid
    fm.MediaStorageSOPInstanceUID = generate_uid(prefix=ORG_ROOT + ".")
    fm.TransferSyntaxUID = ExplicitVRLittleEndian
    fm.ImplementationClassUID = generate_uid(prefix=ORG_ROOT + ".")

    ds = Dataset()
    ds.file_meta = fm
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    # SOP
    ds.SOPClassUID = sop_uid
    ds.SOPInstanceUID = fm.MediaStorageSOPInstanceUID

    # Patient
    ds.PatientName = pt["name"]
    ds.PatientID = pt["id"]
    ds.PatientBirthDate = pt["dob"]
    ds.PatientSex = pt["sex"]

    # Study
    ds.StudyInstanceUID = study["uid"]
    ds.StudyDate = study["date"]
    ds.StudyTime = "101500"
    ds.StudyID = study["id"]
    ds.AccessionNumber = study["accession"]
    ds.StudyDescription = study["desc"]
    ds.ReferringPhysicianName = "REFERRING^DOCTOR^TEST"

    # Series
    ds.SeriesInstanceUID = series["uid"]
    ds.SeriesNumber = series["number"]
    ds.Modality = modality
    ds.SeriesDescription = f"{modality} series {series['number']}"

    # Instance
    ds.InstanceNumber = inst_num
    ds.ImageType = ["ORIGINAL", "PRIMARY"]

    # Image pixel module
    px = make_pixels(rows, cols, is_rgb, seed)
    ds.SamplesPerPixel = spp
    ds.Rows = rows
    ds.Columns = cols
    if is_rgb:
        ds.PhotometricInterpretation = "RGB"
        ds.PlanarConfiguration = 0
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
    else:
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
    ds.PixelData = px.tobytes()
    return ds


def rand_dob(rng):
    year = rng.randint(1945, 2010)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return f"{year:04d}{month:02d}{day:02d}"


def rand_studydate(rng, within_days):
    # spread studies over the past `within_days` so date-range queries hit
    delta = rng.randint(0, within_days)
    d = datetime.date.today() - datetime.timedelta(days=delta)
    return d.strftime("%Y%m%d")


def main():
    p = argparse.ArgumentParser(description="Generate synthetic DICOM test data.")
    p.add_argument("--outdir", default="/data/dicom")
    p.add_argument("--patients", type=int, default=8)
    p.add_argument("--max-studies", type=int, default=3)
    p.add_argument("--max-series", type=int, default=2)
    p.add_argument("--max-instances", type=int, default=4)
    p.add_argument("--within-days", type=int, default=60,
                   help="spread study dates across this many past days")
    p.add_argument("--seed", type=int, default=1337)
    args = p.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(args.outdir, exist_ok=True)
    total = 0

    for pi in range(args.patients):
        pt = {
            "name": f"{rng.choice(LAST)}^{rng.choice(FIRST)}",
            "id": f"TEST{1000 + pi:04d}",
            "dob": rand_dob(rng),
            "sex": rng.choice(["M", "F", "O"]),
        }
        n_studies = rng.randint(1, args.max_studies)
        for si in range(n_studies):
            modality = rng.choice(list(MODALITIES.keys()))
            study = {
                "uid": generate_uid(prefix=ORG_ROOT + "."),
                "date": rand_studydate(rng, args.within_days),
                "id": f"S{si+1}",
                "accession": f"ACC{rng.randint(100000, 999999)}",
                "desc": rng.choice(STUDY_DESC[modality]),
            }
            n_series = rng.randint(1, args.max_series)
            for sei in range(n_series):
                series = {
                    "uid": generate_uid(prefix=ORG_ROOT + "."),
                    "number": sei + 1,
                }
                n_inst = rng.randint(1, args.max_instances)
                for ii in range(n_inst):
                    seed = rng.randint(0, 2**31 - 1)
                    ds = build_instance(pt, study, series, modality,
                                        ii + 1, seed)
                    d = os.path.join(args.outdir, pt["id"],
                                     study["uid"], series["uid"])
                    os.makedirs(d, exist_ok=True)
                    path = os.path.join(d, ds.SOPInstanceUID + ".dcm")
                    ds.save_as(path, enforce_file_format=True)
                    total += 1
        print(f"  patient {pt['id']} ({pt['name']}): {n_studies} studies")

    print(f"[+] Generated {total} DICOM instances for {args.patients} "
          f"patients under {args.outdir}")


if __name__ == "__main__":
    main()
