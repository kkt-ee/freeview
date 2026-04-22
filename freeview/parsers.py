"""Parsers for common FreeSurfer stats files: `aseg`, `wmparc`, `aparc` (lh/rh)."""
from pathlib import Path
import re
import pandas as pd
import logging

logger = logging.getLogger("freeview")


def _read_table_lines(path):
    with open(path, "r") as f:
        lines = [l.rstrip("\n") for l in f]
    # skip header comments
    data_lines = [l for l in lines if l and not l.startswith("#")]
    return data_lines


def parse_aseg(path):
    """Parse an `aseg.stats` file into a DataFrame.

    Columns: Index, SegId, NVoxels, Volume_mm3, StructName, normMean, normStdDev, normMin, normMax, normRange
    """
    data_lines = _read_table_lines(path)
    # find header row starting with ColHeaders or the first numeric row
    start = 0
    for i, l in enumerate(data_lines):
        if l.strip().startswith("ColHeaders"):
            start = i + 1
            break
        # some files don't have ColHeaders, they directly list rows
    rows = []
    for l in data_lines[start:]:
        # split by whitespace but keep struct names with spaces
        parts = re.split(r"\s{2,}|\t", l.strip())
        # fallback to simple split
        if len(parts) < 5:
            parts = l.split()
        # Expect last 6 fields are numbers (norm stats)
        # first cols: Index SegId NVoxels Volume_mm3 StructName (which may be multiple tokens)
        if len(parts) >= 10:
            try:
                idx = parts[0]
                segid = parts[1]
                nvox = parts[2]
                vol = parts[3]
                # struct name may be in middle; reconstruct
                name = " ".join(parts[4:-5])
                rest = parts[-5:]
                rows.append([int(idx), int(segid), int(nvox), float(vol), name] + [float(x) for x in rest])
            except Exception:
                logger.exception("Failed to parse aseg line: %s", l)
    cols = ["Index", "SegId", "NVoxels", "Volume_mm3", "StructName", "normMean", "normStdDev", "normMin", "normMax", "normRange"]
    df = pd.DataFrame(rows, columns=cols)
    return df


def parse_wmparc(path):
    # same format as aseg
    return parse_aseg(path)


def parse_aparc(path):
    """Parse lh/rh.aparc.stats (surface) into DataFrame.

    Columns: StructName, NumVert, SurfArea, GrayVol, ThickAvg, ThickStd, MeanCurv, GausCurv, FoldInd, CurvInd
    """
    data_lines = _read_table_lines(path)
    # find header row
    start = 0
    for i, l in enumerate(data_lines):
        if l.strip().startswith("ColHeaders"):
            start = i + 1
            break
    rows = []
    for l in data_lines[start:]:
        # typical line: regionName <many spaces> numvert surfarea grayvol thickavg thickstd meancurv gauscurv foldind curvind
        parts = re.split(r"\s{2,}|\t", l.strip())
        if len(parts) < 10:
            parts = l.split()
        if len(parts) >= 10:
            try:
                name = parts[0]
                nums = parts[1:]
                row = [name] + [float(x) if ('.' in x or 'e' in x.lower()) else int(x) for x in nums[:9]]
                rows.append(row)
            except Exception:
                logger.exception("Failed to parse aparc line: %s", l)
    cols = ["StructName", "NumVert", "SurfArea", "GrayVol", "ThickAvg", "ThickStd", "MeanCurv", "GausCurv", "FoldInd", "CurvInd"]
    df = pd.DataFrame(rows, columns=cols)
    return df


def autodetect_and_parse(stats_dir: Path):
    """Scan a stats dir and parse known files, returning dict of DataFrames."""
    stats_dir = Path(stats_dir)
    out = {}
    if (stats_dir / "aseg.stats").exists():
        df = parse_aseg(stats_dir / "aseg.stats")
        df["source_file"] = (stats_dir / "aseg.stats").name
        out["aseg"] = df
    if (stats_dir / "wmparc.stats").exists():
        df = parse_wmparc(stats_dir / "wmparc.stats")
        df["source_file"] = (stats_dir / "wmparc.stats").name
        out["wmparc"] = df
    for hemi in ("lh", "rh"):
        for suffix in ("aparc.stats", "aparc.pial.stats", "aparc.a2009s.stats", "aparc.DKTatlas.stats"):
            p = stats_dir / f"{hemi}.{suffix}"
            if p.exists():
                key = f"{hemi}.{suffix.replace('.','_')}"
                df = parse_aparc(p)
                df["source_file"] = p.name
                out[key] = df
    return out
