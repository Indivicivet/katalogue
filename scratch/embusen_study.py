"""
Kinematic Movement Deduction & Embusen Simulator (WIP Study)
-----------------------------------------------------------
Internal analysis script exploring:
1. Foot position tracking (Left vs Right coordinates, angles, and contact primitive).
2. Which foot moves as a function of turn amount, previous stance/lead, new stance/lead, and new facing.
3. JKA heel pivots vs. ball pivots.
4. Identification and classification of ambiguities (e.g. Heian Yondan move 5 vs 7,
   retraction vs advance, yori-ashi, tsugi-ashi, jumping moves).
5. Output of a standalone HTML visual report with interactive 2D foot-coordinate embusen diagrams
   saved exclusively in scratch/embusen_study.html without touching any main catalog files.
"""

import math
import sys
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).parent.parent.resolve()
KATA_DIR = ROOT_DIR / "kata"
TECH_DIR = ROOT_DIR / "techniques"

COMPASS_DEG = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}

TURN_DELTA_DEG = {
    "0": 0,
    "advance": 0,
    None: 0,
    "left_45": -45,
    "right_45": 45,
    "left_90": -90,
    "right_90": 90,
    "left_135": -135,
    "right_135": 135,
    "left_180": -180,
    "right_180": 180,
    "left_225": -225,
    "right_225": 225,
    "left_270": -270,
    "right_270": 270,
    "left_360": 0,
}

# Stance geometric footprints (relative to body center):
# Format: (dx, dy, foot_rot_relative_to_facing, contact)
STANCE_OFFSETS = {
    "zenkutsu_dachi": {
        "left": {"left": (-16, 42, 0, "full"), "right": (16, -42, 30, "full")},
        "right": {"left": (-16, -42, -30, "full"), "right": (16, 42, 0, "full")},
    },
    "kokutsu_dachi": {
        "left": {"left": (0, 36, 0, "full"), "right": (0, -36, 90, "full")},
        "right": {"left": (0, -36, -90, "full"), "right": (0, 36, 0, "full")},
    },
    "kiba_dachi": {
        "left": {"left": (-36, 0, 0, "full"), "right": (36, 0, 0, "full")},
        "right": {"left": (-36, 0, 0, "full"), "right": (36, 0, 0, "full")},
        "both": {"left": (-36, 0, 0, "full"), "right": (36, 0, 0, "full")},
        "none": {"left": (-36, 0, 0, "full"), "right": (36, 0, 0, "full")},
    },
    "kosa_dachi": {
        "left": {"left": (-8, 14, 15, "full"), "right": (8, -14, 20, "ball")},
        "right": {"left": (-8, -14, -20, "ball"), "right": (8, 14, -15, "full")},
    },
    "neko_ashi_dachi": {
        "left": {"left": (0, 20, 0, "ball"), "right": (0, -20, 45, "full")},
        "right": {"left": (0, -20, -45, "full"), "right": (0, 20, 0, "ball")},
    },
    "tsuru_ashi_dachi": {
        "left": {"left": (0, 0, 0, "full"), "right": (0, 16, 0, "airborne")},
        "right": {"left": (0, 16, 0, "airborne"), "right": (0, 0, 0, "full")},
    },
    "heisoku_dachi": {
        "left": {"left": (-5, 0, 0, "full"), "right": (5, 0, 0, "full")},
        "right": {"left": (-5, 0, 0, "full"), "right": (5, 0, 0, "full")},
        "both": {"left": (-5, 0, 0, "full"), "right": (5, 0, 0, "full")},
    }
}


def deduce_moving_foot(prev_step, curr_step, step_index):
    if step_index == 1:
        turn = curr_step.get("turn")
        lead = curr_step.get("lead")
        if turn in ["left_90", "left_45"]:
            return {
                "moving_foot": "left",
                "pivot_foot": "right",
                "pivot_type": "heel",
                "rule": "Move 1: Opening leftward turn steps out with the left foot",
                "ambiguity": None,
            }
        elif turn in ["right_90", "right_45"]:
            return {
                "moving_foot": "right",
                "pivot_foot": "left",
                "pivot_type": "heel",
                "rule": "Move 1: Opening rightward turn steps out with the right foot",
                "ambiguity": None,
            }
        elif turn in ["0", "advance", None]:
            return {
                "moving_foot": lead or "left",
                "pivot_foot": "right" if lead == "left" else "left",
                "pivot_type": "heel",
                "rule": "Move 1: Advance forward steps out with lead foot",
                "ambiguity": None,
            }

    prev_lead = prev_step.get("lead")
    curr_lead = curr_step.get("lead")
    turn = curr_step.get("turn")
    turn_deg = TURN_DELTA_DEG.get(turn, 0)
    curr_stance = curr_step.get("stance")

    if turn_deg == 0:
        if prev_lead and curr_lead and prev_lead != curr_lead:
            return {
                "moving_foot": curr_lead,
                "pivot_foot": prev_lead,
                "pivot_type": "heel",
                "rule": "Straight step-through: rear foot passes forward to become new lead",
                "ambiguity": None,
            }
        elif prev_lead and curr_lead and prev_lead == curr_lead:
            return {
                "moving_foot": "both_sliding",
                "pivot_foot": "none",
                "pivot_type": "slide",
                "rule": "Linear translation with same lead: sliding footwork (yori-ashi / tsugi-ashi)",
                "ambiguity": "Requires distinction between yori-ashi (both slide) and tsugi-ashi (rear gathers then front steps).",
            }
        elif curr_stance in ["tsuru_ashi_dachi", "gankaku_dachi"]:
            standing = curr_lead
            lifted = "right" if standing == "left" else "left"
            return {
                "moving_foot": lifted,
                "pivot_foot": standing,
                "pivot_type": "heel_or_in_place",
                "rule": "Crane stance transition: non-supporting foot lifts into chamber",
                "ambiguity": "Verify if standing foot pulls in slightly or remains anchored.",
            }

    if abs(turn_deg) == 180:
        return {
            "moving_foot": prev_lead,
            "pivot_foot": "right" if prev_lead == "left" else "left",
            "pivot_type": "heel",
            "rule": "180° turn: front foot sweeps across the line; rear foot heel anchors and pivots",
            "ambiguity": None,
        }

    if abs(turn_deg) in [90, 270]:
        if prev_lead == curr_lead:
            return {
                "moving_foot": curr_lead,
                "pivot_foot": "right" if curr_lead == "left" else "left",
                "pivot_type": "heel",
                "rule": "90° turn preserving lead: front foot steps to line, rear pivots on heel",
                "ambiguity": None,
            }
        else:
            return {
                "moving_foot": curr_lead,
                "pivot_foot": prev_lead,
                "pivot_type": "heel",
                "rule": "90° turn with lead change: rear foot swings around anchor front heel",
                "ambiguity": None,
            }

    if abs(turn_deg) in [45, 135, 225]:
        return {
            "moving_foot": curr_lead or "deduced_lead",
            "pivot_foot": prev_lead or "deduced_rear",
            "pivot_type": "heel",
            "rule": "Diagonal turn: stepping foot angles to new line; supporting foot pivots on heel",
            "ambiguity": "Angle geometry depends on whether stepping foot moves to center line or corner line.",
        }

    return {
        "moving_foot": "unknown",
        "pivot_foot": "unknown",
        "pivot_type": "unknown",
        "rule": "General kinematic deduction fallback",
        "ambiguity": f"Unrecognized turn transition: {turn}",
    }


def compute_foot_positions(steps):
    """
    Simulates floor trajectories for both left and right feet
    tracking actual world coordinates (X, Y) and orientations.
    """
    # World frame: X=East, Y=North.
    # Start in shizentai at origin (0, 0), facing North (0 deg)
    l_pos = [-15.0, 0.0, 0.0, "full"]
    r_pos = [15.0, 0.0, 0.0, "full"]

    history = []
    # (step_id, facing, turn, l_pos, r_pos, moving_foot, pivot_foot, pivot_type, ambiguity)

    for i, s in enumerate(steps, start=1):
        prev = steps[i - 2] if i > 1 else None
        ded = deduce_moving_foot(prev, s, i)
        facing = s.get("facing") or "N"
        facing_rad = math.radians(COMPASS_DEG.get(facing, 0))

        stance = s.get("stance", "zenkutsu_dachi")
        lead = s.get("lead", "left")

        # Stance local template
        st_tmpl = STANCE_OFFSETS.get(stance, STANCE_OFFSETS["zenkutsu_dachi"]).get(lead, STANCE_OFFSETS["zenkutsu_dachi"]["left"])
        
        # In a JKA pivot, the pivot foot heel stays on its floor coordinate
        # and rotates to its new stance angle. The moving foot steps to the new stance position.
        pivot = ded["pivot_foot"]
        moving = ded["moving_foot"]

        # Center of hips can be estimated from the pivot foot
        # Rotation matrix from body frame (facing) to world frame
        # In body frame: +Y is Forward (along facing), +X is Right
        cos_f = math.cos(facing_rad)
        sin_f = math.sin(facing_rad)

        def body_to_world(bx, by):
            # X_world = bx * cos_f + by * sin_f
            # Y_world = -bx * sin_f + by * cos_f
            wx = bx * cos_f + by * sin_f
            wy = -bx * sin_f + by * cos_f
            return wx, wy

        # Calculate offset from body center to feet in current stance
        l_bx, l_by, l_rot, l_cnt = st_tmpl["left"]
        r_bx, r_by, r_rot, r_cnt = st_tmpl["right"]

        l_wx, l_wy = body_to_world(l_bx, l_by)
        r_wx, r_wy = body_to_world(r_bx, r_by)

        if pivot == "right":
            # Right foot anchor remains at its current position (or turns on heel)
            # Body center is positioned such that right foot matches
            center_x = r_pos[0] - r_wx
            center_y = r_pos[1] - r_wy
            # New left foot position
            new_lx = center_x + l_wx
            new_ly = center_y + l_wy
            new_rx = r_pos[0]
            new_ry = r_pos[1]
        elif pivot == "left":
            # Left foot anchor remains at its current position
            center_x = l_pos[0] - l_wx
            center_y = l_pos[1] - l_wy
            new_lx = l_pos[0]
            new_ly = l_pos[1]
            new_rx = center_x + r_wx
            new_ry = center_y + r_wy
        else:
            # Linear translation or sliding
            step_dist = 60.0
            dx = math.sin(facing_rad) * step_dist
            dy = math.cos(facing_rad) * step_dist
            new_lx = l_pos[0] + dx
            new_ly = l_pos[1] + dy
            new_rx = r_pos[0] + dx
            new_ry = r_pos[1] + dy

        l_pos = [new_lx, new_ly, COMPASS_DEG.get(facing, 0) + l_rot, l_cnt]
        r_pos = [new_rx, new_ry, COMPASS_DEG.get(facing, 0) + r_rot, r_cnt]

        history.append({
            "step_id": s.get("id"),
            "count": s.get("count"),
            "stance": stance,
            "lead": lead,
            "technique": s.get("technique"),
            "turn": s.get("turn"),
            "facing": facing,
            "kiai": s.get("kiai", False),
            "l_pos": list(l_pos),
            "r_pos": list(r_pos),
            **ded
        })

    return history


def generate_embusen_svg_diagram(history, kata_name):
    """
    Renders an interactive 2D SVG showing every footprint on the floor.
    Blue = Left Foot, Amber = Right Foot.
    Pivots shown with arc markers; Ambiguities highlighted in red dashed strokes.
    """
    # Collect coordinates to determine bounding box
    all_x = []
    all_y = []
    for h in history:
        all_x.extend([h["l_pos"][0], h["r_pos"][0]])
        all_y.extend([h["l_pos"][1], h["r_pos"][1]])

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    pad = 60
    w = max(400, int(max_x - min_x + pad * 2))
    h = max(400, int(max_y - min_y + pad * 2))

    # In screen coords, North (Y+) is upward (-ScreenY)
    def world_to_screen(wx, wy):
        sx = wx - min_x + pad
        sy = (max_y - wy) + pad
        return sx, sy

    svg = []
    svg.append(f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="background:#0f172a; border-radius:8px; width:100%; max-width:850px; height:auto; box-shadow:0 4px 6px -1px rgba(0,0,0,0.3); font-family:sans-serif;">')
    svg.append('<defs>')
    svg.append('<filter id="glow"><feGaussianBlur stdDeviation="2" result="coloredBlur"/><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    svg.append('</defs>')

    # Background grid
    for gx in range(0, w, 50):
        svg.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{h}" stroke="#1e293b" stroke-width="1" />')
    for gy in range(0, h, 50):
        svg.append(f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke="#1e293b" stroke-width="1" />')

    # Draw movement paths between successive center of gravity
    prev_cx, prev_cy = None, None
    for item in history:
        lx, ly = item["l_pos"][0], item["l_pos"][1]
        rx, ry = item["r_pos"][0], item["r_pos"][1]
        cx, cy = (lx + rx) / 2.0, (ly + ry) / 2.0
        scx, scy = world_to_screen(cx, cy)
        if prev_cx is not None:
            stroke_color = "#ef4444" if item["ambiguity"] else "#38bdf8"
            dash = "stroke-dasharray='4,4'" if item["ambiguity"] else ""
            svg.append(f'<line x1="{prev_cx:.1f}" y1="{prev_cy:.1f}" x2="{scx:.1f}" y2="{scy:.1f}" stroke="{stroke_color}" stroke-width="2" opacity="0.6" {dash}/>')
        prev_cx, prev_cy = scx, scy

    # Draw footprints
    for item in history:
        sid = item["step_id"]
        is_kiai = item["kiai"]
        has_ambig = bool(item["ambiguity"])

        for side, pos, color, outline in [
            ("L", item["l_pos"], "#3b82f6", "#93c5fd"),
            ("R", item["r_pos"], "#f59e0b", "#fde68a"),
        ]:
            wx, wy, rot, contact = pos
            sx, sy = world_to_screen(wx, wy)
            
            # Draw individual footprint primitive
            # Foot size: 10 wide, 24 long
            fw, fl = 10, 22
            fill_op = "0.85" if contact == "full" else "0.4"
            svg.append(f'<g transform="translate({sx:.1f}, {sy:.1f}) rotate({rot:.1f})">')
            
            if contact == "ball":
                # Ball of foot: highlight anterior pad
                svg.append(f'<ellipse cx="0" cy="{-fl/4}" rx="{fw/2}" ry="{fl/4}" fill="{color}" fill-opacity="0.9" stroke="{outline}" stroke-width="1.5" />')
                svg.append(f'<ellipse cx="0" cy="{fl/3}" rx="{fw/3}" ry="{fl/5}" fill="none" stroke="{outline}" stroke-width="1" stroke-dasharray="2,2" opacity="0.5" />')
            else:
                # Full plantar sole: heel + ball
                svg.append(f'<rect x="{-fw/2}" y="{-fl/2}" width="{fw}" height="{fl}" rx="{fw/2}" fill="{color}" fill-opacity="{fill_op}" stroke="{outline}" stroke-width="1.5" />')
                # Heel anchor dot
                svg.append(f'<circle cx="0" cy="{fl/3}" r="2" fill="#ffffff" />')

            svg.append('</g>')

        # Center label of step ID
        cx, cy = (item["l_pos"][0] + item["r_pos"][0]) / 2.0, (item["l_pos"][1] + item["r_pos"][1]) / 2.0
        scx, scy = world_to_screen(cx, cy)
        
        lbl_bg = "#dc2626" if is_kiai else ("#b91c1c" if has_ambig else "#1e293b")
        svg.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="9" fill="{lbl_bg}" stroke="#ffffff" stroke-width="1.5" />')
        svg.append(f'<text x="{scx:.1f}" y="{scy+3:.1f}" font-size="9" font-weight="700" fill="#ffffff" text-anchor="middle">{sid}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


def generate_scratch_report():
    test_kata = ["01_heian_shodan.yaml", "04_heian_yondan.yaml", "06_tekki_shodan.yaml"]
    analyzed = []

    for name in test_kata:
        p = KATA_DIR / "jka" / name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                kdata = yaml.safe_load(f)
            steps = kdata.get("steps", [])
            history = compute_foot_positions(steps)
            svg_diag = generate_embusen_svg_diagram(history, kdata.get("name"))
            analyzed.append((kdata, history, svg_diag))

    out_html = ROOT_DIR / "scratch" / "embusen_study.html"
    
    html = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Embusen & Movement Deduction Study • Scratch Report</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1329; color: #e2e8f0; padding: 2rem; margin: 0; }",
        ".container { max-width: 1300px; margin: 0 auto; }",
        ".header { margin-bottom: 2.5rem; border-bottom: 1px solid #1e293b; padding-bottom: 1.5rem; }",
        "h1 { font-size: 2rem; margin: 0 0 0.5rem 0; color: #f8fafc; font-weight: 800; }",
        ".section { background: #111e38; border: 1px solid #1e293b; border-radius: 12px; padding: 2rem; margin-bottom: 3rem; }",
        "h2 { font-size: 1.4rem; margin-top: 0; color: #38bdf8; display: flex; align-items: baseline; justify-content: space-between; }",
        ".flex-view { display: flex; gap: 2rem; align-items: flex-start; flex-wrap: wrap; }",
        ".diagram-col { flex: 1; min-width: 380px; }",
        ".table-col { flex: 1.4; min-width: 500px; max-height: 600px; overflow-y: auto; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; }",
        "table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }",
        "th, td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #1e293b; text-align: left; }",
        "th { background: #1e293b; color: #94a3b8; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; position: sticky; top: 0; }",
        "tr:hover { background: #1e293b; }",
        ".badge-clean { background: #064e3b; color: #6ee7b7; padding: 0.2rem 0.55rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }",
        ".badge-ambiguous { background: #7f1d1d; color: #fca5a5; padding: 0.2rem 0.55rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }",
        ".pill { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }",
        ".pill-left { background: #1e3a8a; color: #bfdbfe; }",
        ".pill-right { background: #78350f; color: #fde68a; }",
        ".pill-heel { background: #581c87; color: #e9d5ff; }",
        ".legend { display: flex; gap: 1.5rem; margin-top: 1rem; font-size: 0.8rem; color: #94a3b8; }",
        ".legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 0.35rem; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class='container'>",
        "<div class='header'>",
        "<h1>🥋 Embusen & Movement Deduction Study</h1>",
        "<p style='color: #94a3b8; margin: 0.25rem 0 0 0;'>Independent Internal Prototype • Tracking left/right foot coordinates, heel-pivot rotations, and mathematical ambiguity boundaries across JKA kata.</p>",
        "</div>",
    ]

    for kdata, history, svg in analyzed:
        ambig_cnt = sum(1 for h in history if h["ambiguity"])
        clean_cnt = len(history) - ambig_cnt
        clean_pct = round((clean_cnt / len(history)) * 100, 1)

        html.append("<div class='section'>")
        html.append(f"<h2><span>{kdata.get('name')} ({kdata.get('kanji')}) &bull; {len(history)} Counts</span><span class='badge-clean'>{clean_pct}% Deduced Cleanly</span></h2>")
        html.append("<div class='flex-view'>")
        
        # Diagram column
        html.append("<div class='diagram-col'>")
        html.append(svg)
        html.append("<div class='legend'>")
        html.append("<span><span class='legend-dot' style='background:#3b82f6;'></span>Left Foot</span>")
        html.append("<span><span class='legend-dot' style='background:#f59e0b;'></span>Right Foot</span>")
        html.append("<span><span class='legend-dot' style='background:#ffffff;'></span>Heel Anchor Dot</span>")
        html.append("<span><span class='legend-dot' style='background:#ef4444;'></span>Ambiguity Flag</span>")
        html.append("</div></div>")

        # Table column
        html.append("<div class='table-col'>")
        html.append("<table>")
        html.append("<thead><tr><th>#</th><th>Stance / Lead</th><th>Turn & Facing</th><th>Moving</th><th>Anchor Foot</th><th>Deduction Status / Ambiguity Flag</th></tr></thead><tbody>")

        for h in history:
            m_pill = f"<span class='pill pill-{h['moving_foot']}'>{h['moving_foot']}</span>" if h['moving_foot'] in ['left', 'right'] else f"<span>{h['moving_foot']}</span>"
            p_pill = f"<span class='pill pill-{h['pivot_foot']}'>{h['pivot_foot']}</span>" if h['pivot_foot'] in ['left', 'right'] else f"<span>{h['pivot_foot']}</span>"
            
            if h["ambiguity"]:
                status_td = f"<span class='badge-ambiguous'>AMBIGUITY</span> <span style='font-size:0.75rem; color:#f87171;'>{h['ambiguity']}</span>"
            else:
                status_td = f"<span class='badge-clean'>DEDUCED</span> <span style='font-size:0.75rem; color:#94a3b8;'>{h['rule']}</span>"

            html.append(f"<tr><td><strong>{h['step_id']}</strong></td><td>{h['stance']}<br><small style='color:#64748b;'>{h['lead']}</small></td><td>{h['turn']}<br>&rarr; {h['facing']}</td><td>{m_pill}</td><td>{p_pill}</td><td>{status_td}</td></tr>")

        html.append("</tbody></table></div>")
        html.append("</div></div>")

    html.append("</div></body></html>")

    with open(out_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"Scratch report generated at: {out_html}")


if __name__ == "__main__":
    generate_scratch_report()
