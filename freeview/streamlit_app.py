"""Minimal Streamlit app to inspect FreeSurfer stats CSVs.

Usage:
  streamlit run freeview/streamlit_app.py -- ./output/consolidated_stats.csv ./output/summary.csv
If no args provided, defaults to `./output/consolidated_stats.csv` and `./output/summary.csv`.
"""
import sys
from pathlib import Path
import tempfile
import zipfile
import streamlit as st
import logging
logger = logging.getLogger("freeview")
import pandas as pd
import plotly.express as px

# Always prioritize this workspace package over any installed package.
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from freeview import stats2csv


def load_df(path):
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def get_metric(df, candidates):
    if df.empty:
        return None
    row = df.iloc[0]
    for c in candidates:
        if c in df.columns:
            return row[c]
    # substring match
    for col in df.columns:
        for c in candidates:
            if c.lower() in col.lower():
                return row[col]
    return None


def _find_stats_dir(root: Path) -> Path | None:
    """Search extracted archive for a FreeSurfer `stats` directory or a file `aseg.stats`.

    Returns the Path to the stats directory or None if not found.
    """
    # look for a directory named 'stats'
    for p in root.rglob("stats"):
        if p.is_dir():
            return p
    # look for aseg.stats file anywhere
    for f in root.rglob("aseg.stats"):
        return f.parent
    return None


def _safe_extract_zip(zip_path: Path, extract_dir: Path):
    """Safely extract a zip file into extract_dir, preventing path traversal.

    Raises RuntimeError if a zip member would extract outside extract_dir.
    """
    extract_dir = Path(extract_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.infolist():
            member_name = member.filename
            # skip directory entries
            if member_name.endswith("/"):
                continue
            dest = extract_dir.joinpath(member_name)
            try:
                dest_resolved = dest.resolve()
            except Exception:
                raise RuntimeError(f"Invalid zip member path: {member_name}")
            if not str(dest_resolved).startswith(str(extract_dir.resolve())):
                raise RuntimeError(f"Unsafe zip entry detected: {member_name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(dest_resolved, "wb") as out:
                out.write(src.read())


def _normalize_uploaded_parts(upload_name: str) -> list[str]:
    """Normalize an uploaded file path into safe path components."""
    raw = str(upload_name).replace("\\", "/")
    parts = [p for p in raw.split("/") if p and p not in {".", ".."}]
    if parts and parts[0].endswith(":"):
        parts[0] = parts[0].replace(":", "")
    return parts


def _validate_stats_folder_upload(uploaded_files) -> tuple[bool, str]:
    """Validate directory upload to only allow a folder named `stats` with `.stats` files."""
    if not uploaded_files:
        return False, "Please upload a folder named 'stats'."

    root_parts = set()
    for up in uploaded_files:
        parts = _normalize_uploaded_parts(getattr(up, "name", ""))
        if not parts:
            return False, "One uploaded item has an invalid path."

        filename = parts[-1]
        if not filename.lower().endswith(".stats"):
            return False, "Only .stats files are allowed in the uploaded folder."

        if len(parts) < 2:
            return False, "Please select the folder named 'stats' directly, not individual files."

        root_parts.add(parts[0].lower())

    if root_parts != {"stats"}:
        return False, "Please upload only the folder named 'stats'."

    return True, ""


def _select_local_folder() -> str | None:
    """Open a native folder selection dialog and return the selected path.

    This runs on the Streamlit server process, so only works when running locally.
    Returns None if selection failed or was cancelled.
    """
    # No native folder-picker here to keep the app cross-platform.
    # Use the `Local path` input or the uploader (select files or zip).
    return None



def main():
    st.set_page_config(page_title="Freeview Stats Viewer", layout="wide")
    args = sys.argv[1:]
    consolidated_path = args[0] if len(args) >= 1 else "./output/consolidated_stats.csv"
    summary_path = args[1] if len(args) >= 2 else "./output/summary.csv"

    st.title("Freeview — Stats Viewer")
    # show patient timestamp under the main title when available
    try:
        main_patient = st.session_state.get("patient_token")
    except Exception:
        main_patient = None
    if not main_patient:
        try:
            summary_df = load_df(summary_path)
            if not summary_df.empty:
                if "patient" in summary_df.columns and pd.notna(summary_df.iloc[0]["patient"]):
                    main_patient = str(summary_df.iloc[0]["patient"])
                elif "subject" in summary_df.columns and pd.notna(summary_df.iloc[0]["subject"]):
                    main_patient = str(summary_df.iloc[0]["subject"])
        except Exception:
            main_patient = None
    if main_patient:
        st.markdown(f"**Patient timestamp:** {main_patient}")

    st.sidebar.header("Input")

    consolidated_updated = None
    summary_updated = None

    if "last_upload_fingerprint" not in st.session_state:
        st.session_state["last_upload_fingerprint"] = None

    input_mode = st.sidebar.radio("Input method", ("Upload folder", "Path"), index=0)

    uploaded = None
    stats_dir = ""
    if input_mode == "Upload folder":
        uploaded = st.sidebar.file_uploader(
            "Upload stats folder (select folder directly)",
            type=["stats"],
            accept_multiple_files="directory",
            key="uploader",
        )
        st.sidebar.info("Only a folder named 'stats' with .stats files is accepted when uploading.")
    else:
        stats_dir = st.sidebar.text_input("Path to FreeSurfer stats directory", value="", key="stats_dir_input")

    # Output directory placed below the input area
    out_dir = st.sidebar.text_input("Output directory for CSVs", value="./output", key="out_dir")
    run_button = st.sidebar.button("Upload", key="upload_btn") if input_mode == "Path" else False

    # handle actions
    if input_mode == "Upload folder":
        if not uploaded:
            st.session_state["last_upload_fingerprint"] = None
        else:
            files_to_process = uploaded if isinstance(uploaded, list) else [uploaded]
            upload_fingerprint = (
                tuple(
                    sorted(
                        (str(getattr(up, "name", "")), int(getattr(up, "size", -1)))
                        for up in files_to_process
                    )
                ),
                str(out_dir),
            )
            if st.session_state.get("last_upload_fingerprint") != upload_fingerprint:
                try:
                    is_valid_upload, upload_message = _validate_stats_folder_upload(files_to_process)
                    if not is_valid_upload:
                        st.sidebar.error(upload_message)
                    else:
                        with tempfile.TemporaryDirectory() as td:
                            td_path = Path(td)
                            extract_dir = td_path / "extracted"
                            extract_dir.mkdir()
                            for up in files_to_process:
                                fname = up.name
                                # preserve folder structure when browsers provide relative paths
                                # normalize separators and reject parent-traversal components
                                try:
                                    parts = _normalize_uploaded_parts(fname)
                                    fpath = extract_dir.joinpath(*parts)
                                except Exception:
                                    # fallback: use basename only
                                    from pathlib import PurePosixPath

                                    fpath = extract_dir / PurePosixPath(fname).name
                                fpath.parent.mkdir(parents=True, exist_ok=True)
                                with open(fpath, "wb") as f:
                                    try:
                                        f.write(up.getbuffer())
                                    except Exception:
                                        # some UploadedFile objects expose read()
                                        f.write(up.read())
                            stats_found = _find_stats_dir(extract_dir)
                            if stats_found is None:
                                st.sidebar.error("No valid stats directory was found in the uploaded folder.")
                            else:
                                out_for_upload = out_dir or str(td_path / "output")
                                patient_token = stats2csv.convert_stats_dir(str(stats_found), out_for_upload)
                                if patient_token:
                                    st.session_state["patient_token"] = patient_token
                                st.sidebar.success(f"Wrote CSVs to {out_for_upload}")
                                consolidated_updated = str(Path(out_for_upload) / "consolidated_stats.csv")
                                summary_updated = str(Path(out_for_upload) / "summary.csv")
                except Exception as e:
                    st.sidebar.error(f"Upload/convert failed: {e}")
                finally:
                    st.session_state["last_upload_fingerprint"] = upload_fingerprint
    elif run_button:
        try:
            stats_dir_clean = stats_dir.strip()
            if not stats_dir_clean:
                st.sidebar.error("Please enter a stats directory path before clicking Upload.")
            else:
                if not Path(stats_dir_clean).exists():
                    st.sidebar.error("Local path does not exist.")
                else:
                    patient_token = stats2csv.convert_stats_dir(stats_dir_clean, out_dir)
                    if patient_token:
                        st.session_state["patient_token"] = patient_token
                    st.sidebar.success(f"Wrote CSVs to {out_dir}")
                    consolidated_updated = str(Path(out_dir) / "consolidated_stats.csv")
                    summary_updated = str(Path(out_dir) / "summary.csv")
        except Exception as e:
            st.sidebar.error(f"Conversion failed: {e}")

    # prefer updated paths from conversions
    summary_path = summary_updated or summary_path
    consolidated_path = consolidated_updated or consolidated_path
    summary = load_df(summary_path)
    if not summary.empty:
        col1, col2, col3, col4 = st.columns(4)
        etiv = get_metric(summary, ["eTIV", "EstimatedTotalIntraCranialVol"]) 
        brainseg = get_metric(summary, ["BrainSegVol", "BrainSeg"]) 
        cortex = get_metric(summary, ["CortexVol", "Cortex"]) 
        vent = get_metric(summary, ["VentricleChoroidVol", "VentricleChoroidVol"]) 
        if etiv is not None:
            col1.metric("eTIV (mm³)", f"{etiv:,.0f}")
        if brainseg is not None:
            col2.metric("BrainSegVol (mm³)", f"{brainseg:,.0f}")
        if cortex is not None:
            col3.metric("CortexVol (mm³)", f"{cortex:,.0f}")
        if vent is not None:
            col4.metric("VentricleChoroidVol (mm³)", f"{vent:,.0f}")

    df = load_df(consolidated_path)
    if df.empty:
        st.warning(f"No consolidated CSV found at {consolidated_path}. Run stats2csv first.")
        return

    st.sidebar.header("Filters")
    sources = df["source"].unique().tolist()
    sel_source = st.sidebar.selectbox("Source", sources)
    df2 = df[df["source"] == sel_source]

    # Downloads (consolidated, summary, and current view)
    st.sidebar.header("Downloads")
    # determine patient token: prefer selected source (`df2`), then consolidated `df`, then `summary`, then session state
    patient = None
    try:
        if "patient" in df2.columns:
            vals = df2["patient"].dropna().unique().tolist()
            if vals:
                patient = str(vals[0]) if len(vals) == 1 else f"Multiple({len(vals)})"
    except Exception:
        patient = None
    if not patient:
        try:
            if "patient" in df.columns:
                vals = df["patient"].dropna().unique().tolist()
                if vals:
                    patient = str(vals[0])
        except Exception:
            patient = None
    if not patient and not summary.empty:
        try:
            if "patient" in summary.columns:
                patient = str(summary.iloc[0]["patient"])
            elif "subject" in summary.columns:
                patient = str(summary.iloc[0]["subject"])
        except Exception:
            patient = None
    if not patient:
        patient = st.session_state.get("patient_token") or "patient"
    try:
        cons_csv = df.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(
            "Download consolidated CSV",
            cons_csv,
            file_name=f"{patient}_consolidated_stats.csv",
            mime="text/csv",
        )
    except Exception as e:
        logger.exception("Failed to prepare consolidated CSV for download: %s", e)
    if not summary.empty:
        sum_csv = summary.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(
            "Download summary CSV",
            sum_csv,
            file_name=f"{patient}_summary.csv",
            mime="text/csv",
        )

    # Prefer the original stats filename when available; show source key then filename
    stats_file = None
    if "source_file" in df2.columns:
        vals = df2["source_file"].dropna().unique().tolist()
        if vals:
            stats_file = Path(vals[0]).name
    if stats_file:
        title_text = f"Stats file: {stats_file}"
    else:
        title_text = f"Stats: {sel_source}"
    st.header(title_text)
    # show patient timestamp below the header when available (derive from selected view first)
    try:
        display_patient = None
        if "patient" in df2.columns:
            vals = df2["patient"].dropna().unique().tolist()
            if vals:
                display_patient = str(vals[0]) if len(vals) == 1 else f"Multiple ({len(vals)})"
        if not display_patient and not summary.empty:
            if "patient" in summary.columns:
                display_patient = str(summary.iloc[0]["patient"])
            elif "subject" in summary.columns:
                display_patient = str(summary.iloc[0]["subject"])
        if not display_patient:
            display_patient = st.session_state.get("patient_token")
    except Exception:
        display_patient = None
    if display_patient:
        st.markdown(f"**Patient timestamp:** {display_patient}")
    # Prefer meaningful columns (non-empty) — handle volumetric, cortical, and generic numeric sources
    def _count_nonnull(col: str) -> int:
        return int(df2[col].notna().sum()) if col in df2.columns else 0

    vol_count = _count_nonnull("Volume_mm3")
    gray_count = _count_nonnull("GrayVol")

    if vol_count > 0 and vol_count >= gray_count:
        st.subheader("Regional volumes")
        vol = df2[["StructName", "Volume_mm3"]].dropna()
        vol = vol.sort_values("Volume_mm3", ascending=False)
        # adapt Top N slider to the number of available rows and default to max
        n_vol = len(vol)
        max_vol = max(1, n_vol)
        topn = st.sidebar.slider("Top N", 1, max_vol, max_vol, key=f"topn_{sel_source}")
        fig = px.bar(vol.head(topn), x="StructName", y="Volume_mm3", labels={"Volume_mm3":"Volume (mm³)"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vol.head(200))
        try:
            view_csv = df2.to_csv(index=False).encode("utf-8")
            st.download_button("Download current view (CSV)", view_csv, file_name=f"{patient}_view.csv", mime="text/csv")
        except Exception as e:
            logger.exception("Failed to prepare current view CSV download: %s", e)
    elif gray_count > 0:
        st.subheader("Cortical parcels — Gray matter volume")
        vol = df2[["StructName", "GrayVol", "ThickAvg"]].dropna()
        vol = vol.sort_values("GrayVol", ascending=False)
        # adapt Top N slider to the number of available rows and default to max
        n_gray = len(vol)
        max_gray = max(1, n_gray)
        topn = st.sidebar.slider("Top N", 1, max_gray, max_gray, key=f"topn_{sel_source}")
        fig = px.bar(vol.head(topn), x="StructName", y="GrayVol", labels={"GrayVol":"Gray Matter Volume (mm³)"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vol.head(200))
        try:
            view_csv = df2.to_csv(index=False).encode("utf-8")
            st.download_button("Download current view (CSV)", view_csv, file_name=f"{patient}_view.csv", mime="text/csv")
        except Exception as e:
            logger.exception("Failed to prepare current view CSV download: %s", e)
    else:
        # Generic numeric visualizer: let user pick any numeric column present
        numeric_cols = df2.select_dtypes(include=["number"]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if _count_nonnull(c) > 0]
        if numeric_cols:
            metric = st.sidebar.selectbox("Metric to plot", numeric_cols)
            plot_type = st.sidebar.radio("Plot type", ("Bar (top N)", "Histogram", "Boxplot"))
            if plot_type == "Bar (top N)":
                plot_df = df2[["StructName", metric]].dropna().sort_values(metric, ascending=False)
                n_plot = len(plot_df)
                max_plot = max(1, n_plot)
                topn = st.sidebar.slider("Top N", 1, max_plot, max_plot, key=f"topn_{sel_source}_{metric}")
                fig = px.bar(plot_df.head(topn), x="StructName", y=metric, labels={metric: metric})
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(plot_df.head(200))
            elif plot_type == "Histogram":
                fig = px.histogram(df2, x=metric)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df2[["StructName", metric]].dropna().head(200))
            else:
                fig = px.box(df2, y=metric)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df2[["StructName", metric]].dropna().head(200))
            try:
                view_csv = df2.to_csv(index=False).encode("utf-8")
                st.download_button("Download current view (CSV)", view_csv, file_name=f"{patient}_view.csv", mime="text/csv")
            except Exception as e:
                logger.exception("Failed to prepare current view CSV download: %s", e)
        else:
            st.dataframe(df2)
            try:
                view_csv = df2.to_csv(index=False).encode("utf-8")
                st.download_button("Download current view (CSV)", view_csv, file_name=f"{patient}_view.csv", mime="text/csv")
            except Exception as e:
                logger.exception("Failed to prepare current view CSV download: %s", e)


if __name__ == "__main__":
    main()
