"""High-level orchestration to convert a stats directory into CSV files."""
from pathlib import Path
import logging
import tempfile
import pandas as pd
from .parsers import autodetect_and_parse
from .summary import write_summary

logger = logging.getLogger("freeview")


def convert_stats_dir(stats_dir: str, out_dir: str):
    stats_dir = Path(stats_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = autodetect_and_parse(stats_dir)
    # write a summary CSV with global KPIs parsed from headers (capture df)
    try:
        summary_df = write_summary(stats_dir, out_dir)
    except Exception as e:
        logger.exception("Failed to write summary.csv: %s", e)
        summary_df = None

    # Prefer the directory structure to derive a patient token, picking a
    # meaningful ancestor (e.g., .../Patient/Session/A_T1/stats -> Patient).
    # Avoid using transient names like tmp* or extraction folders.
    patient_token = None

    def _is_temp_name(n: str) -> bool:
        if not n:
            return True
        nl = n.lower()
        if nl.startswith("tmp"):
            return True
        if nl in {"extracted", "temp", "tmp"}:
            return True
        return False

    try:
        parents = list(stats_dir.parents)
        # Prefer the parent.parent (index 1) which commonly holds the session/patient token
        if len(parents) >= 2:
            cand = parents[1].name
            if not _is_temp_name(cand) and cand.lower() != "stats":
                patient_token = cand
        # If not found, scan ancestors (skip immediate parent which is often A_T1)
        if not patient_token:
            for anc in parents[1:]:
                n = anc.name
                if n and not _is_temp_name(n) and n.lower() != "stats":
                    patient_token = n
                    break
    except Exception:
        patient_token = None

    # If summary provides a subject and patient token is empty, fallback to that.
    if (not patient_token or patient_token == "") and summary_df is not None and "subject" in summary_df.columns:
        try:
            val = summary_df.iloc[0].get("subject")
            if val:
                patient_token = str(val)
        except Exception:
            pass

    # final fallback: prefer stats_dir.parent name if reasonable, otherwise use a stable placeholder
    if not patient_token:
        try:
            if len(parents) >= 2 and not _is_temp_name(parents[1].name):
                patient_token = parents[1].name
            elif len(parents) >= 1 and not _is_temp_name(parents[0].name):
                patient_token = parents[0].name
            elif stats_dir.name and stats_dir.name.lower() != "stats":
                patient_token = stats_dir.name
            else:
                patient_token = "uploaded"
        except Exception:
            patient_token = "uploaded"

    # Ensure parsed dataframes include the patient token as a column (first column)
    for name, df in parsed.items():
        if "patient" not in df.columns:
            df.insert(0, "patient", patient_token)
        csv_name = out_dir / f"{name}.csv"
        df.to_csv(csv_name, index=False)
    # produce a consolidated table: include patient and source
    consolidated = []
    for name, df in parsed.items():
        df2 = df.copy()
        if "source" not in df2.columns:
            # place source after patient so patient remains the first column
            df2.insert(1, "source", name)
        consolidated.append(df2)
    if consolidated:
        pd.concat(consolidated, ignore_index=True).to_csv(out_dir / "consolidated_stats.csv", index=False)
    # update summary CSV to include patient token as first column when possible
    try:
        if summary_df is not None:
            if "patient" not in summary_df.columns:
                summary_df.insert(0, "patient", patient_token)
            summary_df.to_csv(out_dir / "summary.csv", index=False)
    except Exception:
        logger.exception("Failed to update summary.csv with patient token")

    print(f"Wrote {len(parsed)} CSV(s) + summary to {out_dir}")
    return patient_token
