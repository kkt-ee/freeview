"""Extract global summary measures from FreeSurfer stats headers."""
from pathlib import Path
import re
import pandas as pd


def _parse_measures_from_file(path: Path):
    measures = {}
    subject = None
    with open(path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line.startswith("#"):
                continue
            txt = line.lstrip("#").strip()
            # subjectname can appear as: "subjectname A_T1"
            if txt.lower().startswith("subjectname"):
                parts = txt.split()
                if len(parts) >= 2:
                    subject = parts[1]
                continue
            # Measure lines: "Measure Key1, Key2, Description, value, units"
            if txt.startswith("Measure "):
                rest = txt[len("Measure "):]
                parts = [p.strip() for p in rest.split(",")]
                if len(parts) >= 2:
                    # prefer the second token as short key (if available)
                    key = parts[1]
                    # value is usually the second-to-last token
                    try:
                        val = float(parts[-2])
                    except (ValueError, TypeError):
                        # try to find first numeric token from right
                        val = None
                        for token in reversed(parts):
                            try:
                                val = float(token)
                                break
                            except (ValueError, TypeError):
                                continue
                    if val is not None:
                        measures[key] = val
    return subject, measures


def extract_summary(stats_dir: str):
    """Scan a stats directory and extract global measures into a single-row DataFrame.

    Returns a DataFrame with one row containing parsed measure keys (e.g. `eTIV`,
    `BrainSegVol`, `CortexVol`, ...). The `subject` column is added if present.
    """
    stats_dir = Path(stats_dir)
    all_measures = {}
    subject = None
    for p in stats_dir.glob("*.stats"):
        s, measures = _parse_measures_from_file(p)
        if s:
            subject = s
        all_measures.update(measures)
    if subject is None:
        # fallback to directory name
        subject = stats_dir.name
    if not all_measures:
        # return empty df with subject
        return pd.DataFrame([{"subject": subject}])
    row = {"subject": subject}
    row.update(all_measures)
    df = pd.DataFrame([row])
    return df


def write_summary(stats_dir: str, out_dir: str):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = extract_summary(stats_dir)
    df.to_csv(out_dir / "summary.csv", index=False)
    return df
