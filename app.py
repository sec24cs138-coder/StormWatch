"""Storm Watch - AI-assisted flood response planning (SIMULATED hackathon prototype)."""
import sys
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.state_manager import ScenarioState          # noqa: E402
from src.advisory_engine import gemini_status        # noqa: E402
from src.map_view import render_map_svg              # noqa: E402

NAVY, ORANGE = "#0B1F3A", "#FF6A13"
# Streamlit renamed use_container_width -> width="stretch"; support both old and new versions.
try:
    _v = tuple(int(x) for x in st.__version__.split(".")[:2])
except Exception:
    _v = (1, 0)
S = {"width": "stretch"} if _v >= (1, 50) else {"use_container_width": True}
st.set_page_config(page_title="Storm Watch", page_icon="🌊", layout="wide")
st.markdown(f"""<style>
.block-container{{padding-top:1.2rem}}
.sw-header{{background:{NAVY};color:#fff;padding:14px 20px;border-radius:12px;display:flex;align-items:center;gap:16px}}
.sw-header h1{{margin:0;font-size:1.7rem;color:#fff}} .sw-header .sub{{color:#C9D6EA;font-size:.9rem}}
.sw-badge{{background:{ORANGE};color:#fff;padding:4px 12px;border-radius:999px;font-weight:700;font-size:.8rem;margin-left:auto;white-space:nowrap}}
.sw-banner{{padding:12px 18px;border-radius:10px;margin:10px 0;color:#fff;font-weight:600}}
.sw-card{{border:1px solid #D5DEEC;border-radius:10px;padding:10px 14px;margin-bottom:8px;background:#fff}}
.sw-step{{display:inline-block;padding:5px 10px;border-radius:8px;margin:2px;font-size:.82rem;font-weight:600}}
.sw-bar{{height:10px;border-radius:5px;background:#E6ECF5;overflow:hidden;display:flex}}
.sw-pill{{padding:2px 9px;border-radius:999px;color:#fff;font-size:.75rem;font-weight:700}}
</style>""", unsafe_allow_html=True)

if "sw" not in st.session_state:
    st.session_state.sw = ScenarioState()
    st.session_state.flash = None
sw: ScenarioState = st.session_state.sw


# ---------------- callbacks (run before the page re-renders) ----------------
def flash(res):
    st.session_state.flash = res


def sync_defaults():
    r, s = sw.suggested_road(), sw.suggested_shelter()
    if r:
        st.session_state["road_sel"] = r
    if s:
        st.session_state["shelter_sel"] = s


def cb_alert(): flash(sw.generate_alert(st.session_state.get("alert_sel")))
def cb_plan(): flash(sw.create_plan()); sync_defaults()
def cb_replan(): flash(sw.replan())
def cb_block(): flash(sw.block_road(st.session_state["road_sel"]))
def cb_restore(): flash(sw.restore_road(st.session_state["road_sel"]))
def cb_full(): flash(sw.mark_shelter_full(st.session_state["shelter_sel"]))
def cb_unfull(): flash(sw.reset_shelter(st.session_state["shelter_sel"]))
def cb_en(): flash(sw.generate_advisory("en"))
def cb_ta(): flash(sw.generate_advisory("ta"))
def cb_approve(): flash(sw.approve())
def cb_reject(): flash(sw.reject())


def cb_reset():
    sw.reset()
    for k in ("road_sel", "shelter_sel", "alert_sel"):
        st.session_state.pop(k, None)
    flash(("success", "Scenario reset to its initial state."))


# ---------------- sidebar controls ----------------
data = sw.data
with st.sidebar:
    st.markdown("### 🎛️ Control panel")
    st.caption("Simulation controls - nothing here contacts real services.")
    st.selectbox("Simulated alert", [a["id"] for a in data["alerts"]], key="alert_sel",
                 format_func=lambda i: next(a["title"] for a in data["alerts"] if a["id"] == i))
    st.button("⚠️ Generate Flood Alert", on_click=cb_alert, **S, key="b_alert")
    st.button("🗺️ Create Response Plan", on_click=cb_plan, **S, type="primary", key="b_plan")
    st.button("🔄 Replan Response", on_click=cb_replan, **S, key="b_replan")
    st.markdown("---")
    used = sw.roads_in_plan()
    st.selectbox("Road X", [r["id"] for r in data["roads"]["roads"]], key="road_sel",
                 format_func=lambda i: f"{i} · {sw.road_names[i]}" + (" ⛔ BLOCKED" if i in sw.blocked else "") + (" ★ on a planned route" if i in used else ""))
    c1, c2 = st.columns(2)
    c1.button("⛔ Block Road X", on_click=cb_block, **S, key="b_block")
    c2.button("✅ Restore Road X", on_click=cb_restore, **S, key="b_restore")
    st.selectbox("Shelter", [s["id"] for s in data["shelters"]], key="shelter_sel",
                 format_func=lambda i: sw.shelter_names[i] + (" 🔴 FULL" if i in sw.full_shelters else ""))
    c3, c4 = st.columns(2)
    c3.button("🏠 Mark Shelter Full", on_click=cb_full, **S, key="b_full")
    c4.button("♻️ Reset Capacity", on_click=cb_unfull, **S, key="b_unfull")
    st.markdown("---")
    c5, c6 = st.columns(2)
    c5.button("📝 English Advisory", on_click=cb_en, **S, key="b_en")
    c6.button("📝 Tamil Advisory", on_click=cb_ta, **S, key="b_ta")
    st.markdown("---")
    with st.expander("⚖️ Risk weights (configurable)"):
        w = sw.config["weights"]
        w["exposure"] = st.slider("Flood exposure", 0.0, 1.0, float(w["exposure"]), 0.05)
        w["population"] = st.slider("Population", 0.0, 1.0, float(w["population"]), 0.05)
        w["vulnerable"] = st.slider("Vulnerable residents", 0.0, 1.0, float(w["vulnerable"]), 0.05)
        st.caption("Weights are normalised. Click **Replan Response** to apply.")
    st.button("🧹 Reset Entire Scenario", on_click=cb_reset, **S, key="b_reset")
    st.caption(f"AI mode: {gemini_status()}")

# ---------------- header, banner, messages ----------------
st.markdown(f"""<div class="sw-header">{(ROOT / 'assets' / 'logo.svg').read_text(encoding='utf-8').replace('width="64" height="64"', 'width="52" height="52"')}
<div><h1>Storm Watch</h1><div class="sub">AI-Assisted Flood Response Planning · from warning to prioritised action</div></div>
<div class="sw-badge">PROTOTYPE · SIMULATED DATA</div></div>""", unsafe_allow_html=True)

if sw.alert:
    colour = {"red": "#C1121F", "orange": "#E8590C"}.get(sw.alert["severity"], "#E8590C")
    st.markdown(f'<div class="sw-banner" style="background:{colour}">🚨 {escape(sw.alert["title"])} — issued {sw.alert["issued_at"]} (SIMULATED)<br>'
                f'<span style="font-weight:400">{escape(sw.alert["summary"])}</span></div>', unsafe_allow_html=True)
else:
    st.info("No active alert. Press **Generate Flood Alert** in the control panel to begin the simulated scenario.")

fl = st.session_state.get("flash")
if fl:
    getattr(st, {"success": "success", "warning": "warning", "error": "error"}.get(fl[0], "info"))(fl[1])
    st.session_state.flash = None

# workflow pipeline
ap = sw.approval_status()
steps = [("Alert Input", bool(sw.alert)), ("Risk Analysis", bool(sw.plan)), ("Shelter Allocation", bool(sw.plan)),
         ("Route Planning", bool(sw.plan)), ("Volunteer Assignment", bool(sw.plan)),
         ("Advisory Generation", bool(sw.advisories["en"])), ("Human Approval", ap == "approved")]
st.markdown(" ➜ ".join(f'<span class="sw-step" style="background:{"#0B1F3A" if ok else "#E6ECF5"};color:{"#fff" if ok else "#5C7AA6"}">{"✔ " if ok else ""}{n}</span>'
                        for n, ok in steps), unsafe_allow_html=True)

plan = sw.plan
if plan:
    total = sum(r["population"] for r in plan["risk"])
    unplaced = sum(u["people"] for u in plan["unserved"])
    m = st.columns(5)
    m[0].metric("Areas affected", len(plan["risk"]))
    m[1].metric("People to evacuate", total)
    m[2].metric("Placed in shelters", total - unplaced)
    m[3].metric("Unplaced", unplaced)
    m[4].metric("Plan version", f"v{sw.plan_version}")
    if ap == "approved":
        st.success(f"✅ Advisory APPROVED for plan v{sw.approval['approved_version']} at {sw.approval['timestamp']} (simulated status only).")
    elif ap == "outdated":
        st.warning(f"⚠️ Previously approved plan is OUTDATED. Plan v{sw.plan_version} needs renewed human approval.")
    elif ap == "rejected":
        st.error(f"❌ Advisory for plan v{sw.approval['plan_version']} was REJECTED at {sw.approval['timestamp']}.")
    elif ap == "pending":
        st.warning(f"⏳ Plan v{sw.plan_version} is awaiting officer approval (Advisory tab).")
    for wmsg in plan["warnings"]:
        st.error(wmsg)

tabs = st.tabs(["📊 Overview", "🏠 Shelters & Routes", "🧑‍🤝‍🧑 Volunteers", "📢 Advisory & Approval", "🧾 Activity Log", "📘 Method & Limits"])
LEVEL_COLOR = {"CRITICAL": "#D7263D", "HIGH": "#FF6A13", "MODERATE": "#F2B134"}

with tabs[0]:
    left, right = st.columns([5, 6])
    with left:
        st.subheader("Affected-area risk ranking")
        if not plan:
            st.caption("Create a response plan to see the ranking.")
        for i, r in enumerate(plan["risk"] if plan else [], 1):
            f = r["factors"]
            seg = "".join(f'<div title="{k}: {f[k]["points"]}" style="width:{f[k]["points"]}%;background:{c}"></div>'
                          for k, c in (("exposure", "#0B1F3A"), ("population", "#4F6FA3"), ("vulnerable", "#FF6A13")))
            st.markdown(f'<div class="sw-card"><b>#{i} {escape(r["name"])}</b> <span class="sw-pill" style="background:{LEVEL_COLOR[r["level"]]}">{r["level"]}</span>'
                        f' <span style="float:right"><b>{r["score"]}</b> / 100</span><div class="sw-bar" style="margin:6px 0">{seg}</div>'
                        f'<small>exposure {f["exposure"]["points"]} · population {f["population"]["points"]} · vulnerable {f["vulnerable"]["points"]} '
                        f'(pop {r["population"]}, vulnerable {r["vulnerable"]})</small></div>', unsafe_allow_html=True)
        if plan and sw.explanation:
            with st.expander("Plain-language explanation (" + sw.explanation["source"] + ")"):
                st.text(sw.explanation["text"])
    with right:
        st.subheader("Scenario map")
        components.html(render_map_svg(sw), height=560)

with tabs[1]:
    st.subheader("Shelter occupancy & remaining capacity")
    if plan:
        cols = st.columns(len(plan["shelter_status"]))
        for col, s in zip(cols, plan["shelter_status"]):
            with col:
                st.markdown(f"**{s['name']}**" + (" 🔴 FULL" if s["marked_full"] else ""))
                used_now = s["occupancy"] + s["planned_additional"]
                st.progress(min(1.0, used_now / s["capacity"]))
                st.caption(f"{used_now}/{s['capacity']} after plan · now {s['occupancy']} · +{s['planned_additional']} planned · {max(0, s['remaining_after_plan'])} free")
    else:
        for s in data["shelters"]:
            st.write(f"**{s['name']}** — {s['initial_occupancy']}/{s['capacity']} occupied" + (" 🔴 FULL" if s["id"] in sw.full_shelters else ""))
    st.subheader("Recommended evacuation routes (Dijkstra)")
    if plan and plan["assignments"]:
        st.dataframe([{"Area": a["area_name"], "People": a["people"], "Shelter": a["shelter_name"],
                       "Route": " → ".join(a["route"]["path_names"]), "Roads": ", ".join(a["route"]["road_ids"]),
                       "Sim. travel (min)": a["route"]["cost"]} for a in plan["assignments"]], **S, hide_index=True)
    elif plan:
        st.error("No feasible route or shelter was found for any area.")
    for u in (plan or {"unserved": []})["unserved"]:
        st.error(f"{u['area_name']}: {u['people']} people unplaced — {u['reason']}")
    if sw.blocked:
        st.warning("Blocked roads: " + ", ".join(f"{i} ({sw.road_names[i]})" for i in sorted(sw.blocked)))

with tabs[2]:
    st.subheader("Volunteer assignments")
    if plan:
        by_id = {v["id"]: v for v in data["volunteers"]}
        st.dataframe([{"Volunteer": v["name"], "Area": next(r["name"] for r in plan["risk"] if r["area_id"] == v["area_id"]),
                       "Role needed": v["skill_needed"], "Skill match": "✔" if v["skill_matched"] else "✖ general support",
                       "Reason": v["reason"]} for v in plan["volunteers"]], **S, hide_index=True)
        for g in plan["volunteer_gaps"]:
            st.warning(f"Unfilled slot at {g['area_id']} ({g['skill']}): {g['reason']}")
        assigned = {v["volunteer_id"] for v in plan["volunteers"]}
        st.caption("Not assigned: " + (", ".join(f"{v['name']}" + ("" if v["available"] else " (unavailable)") for v in data["volunteers"] if v["id"] not in assigned) or "none"))
    else:
        st.dataframe([{"Volunteer": v["name"], "Skills": ", ".join(v["skills"]), "Available": "yes" if v["available"] else "no"} for v in data["volunteers"]],
                     **S, hide_index=True)

with tabs[3]:
    st.subheader("Advisory drafts & human approval")
    st.info("Every public-facing advisory needs officer approval. Approval only changes the simulated status — **no SMS, WhatsApp, email or alert is ever sent.**")
    ca, cb = st.columns(2)
    for col, key, label in ((ca, "en", "English"), (cb, "ta", "தமிழ் (Tamil)")):
        with col:
            adv = sw.advisories[key]
            st.markdown(f"**{label}**")
            if adv:
                st.text_area(label, adv["text"], height=330, disabled=True, label_visibility="collapsed")
                st.caption(f"Source: {adv['source']} · plan v{adv['plan_version']} · {adv['generated_at']} · {adv['note']}")
            else:
                st.caption("Not drafted yet.")
    st.markdown(f"**Plan ID:** `SW-{sw.alert['id'] if sw.alert else '-'}-v{sw.plan_version}` · **Status:** `{ap.upper()}`"
                + (f" · **Timestamp:** {sw.approval['timestamp']}" if sw.approval.get("timestamp") else ""))
    b1, b2, _ = st.columns([1, 1, 3])
    b1.button("✅ Approve Advisory", on_click=cb_approve, type="primary", **S, key="b_approve")
    b2.button("❌ Reject Advisory", on_click=cb_reject, **S, key="b_reject")
    if sw.changes:
        st.subheader("What changed and why")
        for c in reversed(sw.changes):
            with st.expander(f"v{c['version']} · {c['time']} · {c['trigger']}", expanded=c is sw.changes[-1]):
                for line in c["lines"]:
                    st.write("• " + line)

with tabs[4]:
    st.subheader("Agent activity log")
    icon = {"info": "🔹", "success": "🟢", "warning": "🟠", "error": "🔴"}
    for e in reversed(sw.log):
        st.markdown(f"{icon.get(e['level'], '🔹')} `{e['time']}` **{e['agent']}** — {e['message']}")

with tabs[5]:
    st.markdown("""
**Risk score (0–100)** = 100 × (w_exposure × exposure + w_population × population ÷ max_population + w_vulnerable × vulnerable ÷ max_vulnerable),
with weights normalised to sum to 1. Levels: ≥70 CRITICAL, ≥50 HIGH, otherwise MODERATE.

**Shelters:** areas are handled in risk order; each takes the lowest-cost reachable shelter with free places, splitting groups across shelters if needed. Capacity is never exceeded.
**Routes:** NetworkX Dijkstra on simulated travel minutes; blocked roads are removed from the graph. **Volunteers:** skill match first, then nearest; one task each.

**Limitations:** all data is invented; the map is schematic; travel times ignore traffic, depth of water and vehicle type; normalising against the current maximum means scores are relative, not absolute;
Gemini (if enabled) only rewords calculated facts and is validated, with template fallback. Not for real emergency use. Tamil drafts should be reviewed by a fluent speaker.
""")
