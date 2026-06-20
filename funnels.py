"""Per-feature funnel definitions for the Drop Rate by Cutoff tables.

Each step: (col_key, label, event_name, feature_filter)
  feature_filter = None  -> count users with that event (name already unique)
                 = "X"   -> count users with that event AND feature_name = "X"
Base column `user_active` (DAU) and `home_view` (global) are shared/auto-added.
Percentages are computed client-side as step_users / user_active.
"""

FEATURES = {
    "enhance": {
        "label": "Enhance",
        "steps": [
            ("home_view",      "View Home",       "home_view",                 None),
            ("upload",         "Upload Photo",    "enhan_upload_photo_view",    None),
            ("scanning",       "Scanning",        "enhan_scanning_view",        None),
            ("analyze",        "Analyze",         "enhan_analy_view",           None),
            ("generate",       "Generate req",    "service_request",            "Enhance"),
            ("paywall",        "Paywall view",    "iap_view",                   "Enhance"),
            ("result_loading", "Result Loading",  "enhan_result_ld_view",       None),
            ("result",         "Result",          "enhan_result_view",          None),
            ("download",       "Download",        "enhan_result_download_click",None),
            ("share",          "Share",           "enhan_result_share",         None),
        ],
    },
    "i2i": {
        "label": "Image → Image (I2I)",
        "steps": [
            ("home_view",      "View Home",       "home_view",                 None),
            ("click_style",    "Click Style",     "home_style_click",           "I2I"),
            ("upload",         "Upload Photo",    "i2i_upload_photo_view",      None),
            ("generate",       "Generate req",    "service_request",            "I2I"),
            ("paywall",        "Paywall view",    "iap_view",                   "I2I"),
            ("result_loading", "Result Loading",  "i2i_result_ld_view",         None),
            ("result",         "Result",          "i2i_result_view",            None),
            ("download",       "Download",        "i2i_result_download_click",  None),
            ("share",          "Share",           "i2i_result_share",           None),
        ],
    },
    "i2v": {
        "label": "Image → Video (I2V)",
        "steps": [
            ("home_view",      "View Home",       "home_view",                 None),
            ("click_style",    "Click Style",     "home_style_click",           "I2V"),
            ("upload",         "Upload Photo",    "i2v_upload_photo_view",      None),
            ("generate",       "Generate req",    "service_request",            "I2V"),
            ("paywall",        "Paywall view",    "iap_view",                   "I2V"),
            ("result_loading", "Result Loading",  "i2v_result_ld_view",         None),
            ("result",         "Result",          "i2v_result_view",            None),
            ("download",       "Download",        "i2v_result_download_click",  None),
            ("share",          "Share",           "i2v_result_share",           None),
        ],
    },
    "tryon": {
        "label": "Try-on Jersey",
        "steps": [
            ("entry",          "Entry click",     "tryon_entry_click",          None),
            ("preview",        "Preview view",    "tryon_preview_view",         None),
            ("upload_ok",      "Upload OK",       "tryon_upload_photo_success", None),
            ("team_click",     "Team click",      "tryon_preview_team_click",   None),
            ("paywall",        "Paywall view",    "iap_view",                   "Try-on Jersey"),
            ("save",           "Save",            "tryon_preview_save_click",   None),
            ("share",          "Share",           "tryon_preview_share_click",  None),
        ],
    },
    "wclooks": {
        "label": "World Cup Looks",
        "steps": [
            ("entry",          "Entry click",     "wclooks_entry_click",        None),
            ("view",           "Looks view",      "wclooks_view",               None),
            ("upload_ok",      "Upload OK",       "wclooks_upload_photo_success",None),
            ("style_click",    "Style click",     "wclooks_style_click",        None),
            ("paywall",        "Paywall view",    "iap_view",                   "World Cup Looks"),
            ("save",           "Save",            "wclooks_save_click",         None),
            ("share",          "Share",           "wclooks_share_click",        None),
        ],
    },
    "wcvideo": {
        "label": "World Cup Video",
        "steps": [
            ("entry",          "Entry click",     "wcvideo_entry_click",        None),
            ("grid",           "Grid view",       "wcvideo_grid_view",          None),
            ("upload_view",    "Upload view",     "wcvideo_upload_photo_view",  None),
            ("upload_ok",      "Upload OK",       "wcvideo_upload_photo_success",None),
            ("generating",     "Generating",      "wcvideo_generating_view",    None),
            ("result",         "Result",          "wcvideo_result_view",        None),
            ("save",           "Save",            "wcvideo_result_save_click",  None),
            ("share",          "Share",           "wcvideo_result_share_click", None),
        ],
    },
}


def sql_columns():
    """Build the unique set of conditional-distinct columns across all features."""
    cols = {}  # colname -> SQL expr
    for fid, f in FEATURES.items():
        for key, label, ev, ff in f["steps"]:
            colname = f"{fid}__{key}"
            if ff:
                expr = (f"COUNT(DISTINCT IF(ev='{ev}' AND fname='{ff}', uid, NULL))")
            else:
                expr = (f"COUNT(DISTINCT IF(ev='{ev}', uid, NULL))")
            cols[colname] = expr
    return cols
