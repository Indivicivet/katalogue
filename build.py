"""
Katalogue Build Script

Compiles YAML kata definitions, validates referential integrity and rotation geometry,
computes global and per-kata analytics, and renders a zero-dependency static site.
"""

import os
import shutil
import time
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm

ROOT_DIR = Path(__file__).parent.resolve()
DATA_TECH_DIR = ROOT_DIR / "techniques"
KATA_DIR = ROOT_DIR / "kata"
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
DIST_DIR = ROOT_DIR / "dist"
EQUIV_FILE = ROOT_DIR / "equivalents.yaml"

COMPASS_ANGLES = {
    "N": 0,
    "NE": 45,
    "E": 90,
    "SE": 135,
    "S": 180,
    "SW": 225,
    "W": 270,
    "NW": 315,
}

ANGLE_TO_COMPASS = {v: k for k, v in COMPASS_ANGLES.items()}

TURN_DELTAS = {
    "0": 0,
    "advance": 0,
    None: 0,
    "left_45": -45,
    "right_45": 45,
    "left_90": -90,
    "right_90": 90,
    "left_135": -135,
    "right_135": 135,
    "left_180": 180,
    "right_180": 180,
    "left_225": -225,
    "right_225": 225,
    "left_270": -270,
    "right_270": 270,
}


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_rotation(prev_facing: str, turn: str, current_facing: str) -> str | None:
    if prev_facing not in COMPASS_ANGLES or current_facing not in COMPASS_ANGLES:
        return None
    if turn not in TURN_DELTAS:
        return f"Unknown turn specification '{turn}'"

    prev_deg = COMPASS_ANGLES[prev_facing]
    delta = TURN_DELTAS[turn]
    expected_deg = (prev_deg + delta) % 360

    if expected_deg != COMPASS_ANGLES[current_facing]:
        expected_dir = ANGLE_TO_COMPASS.get(expected_deg, f"{expected_deg}deg")
        return (
            f"Rotation mismatch: from {prev_facing} with {turn} "
            f"expects {expected_dir}, but step declares {current_facing}"
        )
    return None


def main():
    start_time = time.perf_counter()
    print("Starting Katalogue build...")

    # 1. Load Master Dictionaries
    stances = load_yaml(DATA_TECH_DIR / "stances.yaml")
    techniques = load_yaml(DATA_TECH_DIR / "techniques.yaml")
    equivalents_groups = load_yaml(EQUIV_FILE) if EQUIV_FILE.exists() else []

    # 2. Build cross-reference map from equivalents.yaml
    # kata_key: "style/id" -> group of equivalent keys
    equiv_map = {}
    for group in equivalents_groups:
        kata_list = group.get("kata", [])
        for k in kata_list:
            equiv_map[k] = [other for other in kata_list if other != k]

    # 3. Discover and Load All Kata Files
    kata_files = sorted(list(KATA_DIR.rglob("*.yaml")))
    print(f"Discovered {len(kata_files)} kata definitions.")

    all_kata = []
    missing_refs = []
    rotation_warnings_count = 0

    print("Validating and parsing kata definitions:")
    for kf in tqdm(kata_files, desc="Parsing Kata", unit="kata"):
        data = load_yaml(kf)
        kata_id = data.get("id")
        style = data.get("style", "jka")
        full_key = f"{style}/{kata_id}"
        data["full_key"] = full_key

        steps = data.get("steps", [])
        rendered_steps = []
        kiai_steps = []
        cat_counts = {
            "block": 0,
            "punch": 0,
            "strike": 0,
            "kick": 0,
            "other": 0,
        }
        prev_facing = "N"

        for step in steps:
            st_key = step.get("stance")
            tech_key = step.get("technique")
            sec_tech_key = step.get("secondary_technique")

            # Validate Stance
            if st_key and st_key not in stances:
                missing_refs.append(
                    f"[{full_key}] Step {step.get('id')}: Unknown stance '{st_key}'"
                )
            # Validate Technique
            if tech_key and tech_key not in techniques:
                missing_refs.append(
                    f"[{full_key}] Step {step.get('id')}: Unknown technique '{tech_key}'"
                )
            if sec_tech_key and sec_tech_key not in techniques:
                missing_refs.append(
                    f"[{full_key}] Step {step.get('id')}: Unknown secondary technique '{sec_tech_key}'"
                )

            # Resolve Objects
            st_obj = stances.get(st_key)
            tech_obj = techniques.get(tech_key)
            sec_tech_obj = techniques.get(sec_tech_key)

            cat = tech_obj.get("category", "other") if tech_obj else "other"
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

            if step.get("kiai"):
                kiai_steps.append(step.get("id"))

            # Rotation check
            turn_str = step.get("turn")
            facing_str = step.get("facing", prev_facing)
            rot_warn = check_rotation(prev_facing, turn_str, facing_str)
            if rot_warn:
                rotation_warnings_count += 1

            prev_facing = facing_str

            rendered_steps.append(
                {
                    **step,
                    "stance_data": st_obj,
                    "tech_data": tech_obj,
                    "sec_tech_data": sec_tech_obj,
                    "category": cat,
                    "rotation_warning": rot_warn,
                }
            )

        total_steps = len(steps)
        cat_percents = {
            k: (round((v / total_steps) * 100, 1) if total_steps > 0 else 0)
            for k, v in cat_counts.items()
        }

        # Base count calculation
        base_counts = set(s.get("count") for s in steps if s.get("count") is not None)
        data["base_count"] = max(base_counts) if base_counts else len(steps)
        data["move_count"] = len(steps)
        data["rendered_steps"] = rendered_steps
        data["kiai_steps"] = kiai_steps
        data["category_counts"] = cat_counts
        data["category_percents"] = cat_percents

        all_kata.append(data)

    # Referential Integrity Assertion
    if missing_refs:
        print("\nFATAL: Referential integrity validation failed!")
        for err in missing_refs:
            print(" -", err)
        raise SystemExit(1)

    print(
        f"Validation passed. Rotational discrepancies flagged: {rotation_warnings_count}"
    )

    # 4. Catalog Index Preparation
    kata_by_key = {k["full_key"]: k for k in all_kata}

    # Attach equivalent object metadata
    for k in all_kata:
        equiv_keys = equiv_map.get(k["full_key"], [])
        k["equivalent_keys"] = equiv_keys
        if equiv_keys:
            eq_obj = kata_by_key.get(equiv_keys[0])
            k["equivalent_kata"] = eq_obj
        else:
            k["equivalent_kata"] = None

    # Group kata by JKA 25, JKA extra (Ji'in), and Shito-ryu
    jka_kata = [k for k in all_kata if k.get("style") == "jka"]
    jka_25 = [k for k in jka_kata if k.get("order", 0) <= 25]
    jka_extra = [k for k in jka_kata if k.get("order", 0) > 25]
    shitoryu_kata = [k for k in all_kata if k.get("style") == "shitoryu"]

    # Collect All Tags
    all_tags = sorted(list(set(t for k in all_kata for t in k.get("tags", []))))

    # 5. Global Analytics Computation (focused on JKA canon)
    jka_all = jka_kata
    total_jka_moves = sum(k["move_count"] for k in jka_all)
    total_jka_kiai = sum(len(k["kiai_steps"]) for k in jka_all)

    global_stance_counts = {}
    global_tech_counts = {}
    global_category_counts = {
        "block": 0,
        "punch": 0,
        "strike": 0,
        "kick": 0,
        "other": 0,
    }

    for k in jka_all:
        for s in k["rendered_steps"]:
            st = s.get("stance")
            if st:
                global_stance_counts[st] = global_stance_counts.get(st, 0) + 1
            tc = s.get("technique")
            if tc:
                global_tech_counts[tc] = global_tech_counts.get(tc, 0) + 1
            cat = s.get("category", "other")
            global_category_counts[cat] = global_category_counts.get(cat, 0) + 1

    global_category_percents = {
        k: (round((v / total_jka_moves) * 100, 1) if total_jka_moves > 0 else 0)
        for k, v in global_category_counts.items()
    }

    stance_ranks = []
    for st_id, cnt in sorted(
        global_stance_counts.items(), key=lambda x: x[1], reverse=True
    ):
        stance_ranks.append(
            {
                "id": st_id,
                "data": stances.get(st_id, {}),
                "count": cnt,
                "percent": (
                    round((cnt / total_jka_moves) * 100, 1)
                    if total_jka_moves > 0
                    else 0
                ),
            }
        )

    top_techniques = []
    for tech_id, cnt in sorted(
        global_tech_counts.items(), key=lambda x: x[1], reverse=True
    )[:15]:
        top_techniques.append(
            {
                "id": tech_id,
                "data": techniques.get(tech_id, {}),
                "count": cnt,
            }
        )

    global_stats = {
        "total_kata": len(jka_all),
        "total_moves": total_jka_moves,
        "total_kiai": total_jka_kiai,
        "category_counts": global_category_counts,
        "category_percents": global_category_percents,
        "stance_ranks": stance_ranks,
        "top_techniques": top_techniques,
    }

    # 6. Initialize Jinja2 Environment
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    env.globals.update(
        {
            "STATUS_MAP": {
                "early_draft": {
                    "ja": "草案",
                    "ja_en": "Early Draft",
                    "ro": "Early Draft",
                    "en": "Early Draft",
                },
                "full_draft": {
                    "ja": "完成稿",
                    "ja_en": "Full Draft",
                    "ro": "Full Draft",
                    "en": "Full Draft",
                },
                "verified": {
                    "ja": "確認済",
                    "ja_en": "Verified",
                    "ro": "Verified",
                    "en": "Verified",
                },
                "reviewed": {
                    "ja": "査読済",
                    "ja_en": "Reviewed",
                    "ro": "Reviewed",
                    "en": "Reviewed",
                },
            },
            "STYLE_MAP": {
                "jka": {
                    "ja": "JKA",
                    "ja_en": "JKA (Shotokan)",
                    "ro": "JKA",
                    "en": "JKA",
                },
                "shitoryu": {
                    "ja": "糸東流",
                    "ja_en": "糸東流 (Shito-ryu)",
                    "ro": "Shito-ryu",
                    "en": "Shito-ryu",
                },
            },
            "LEAD_MAP": {
                "left": {
                    "ja": "左",
                    "ja_en": "左 (left)",
                    "ro": "left",
                    "en": "left",
                },
                "right": {
                    "ja": "右",
                    "ja_en": "右 (right)",
                    "ro": "right",
                    "en": "right",
                },
                "both": {
                    "ja": "両",
                    "ja_en": "両 (both)",
                    "ro": "both",
                    "en": "both",
                },
            },
            "TARGET_MAP": {
                "gedan": {
                    "ja": "下段",
                    "ja_en": "下段 (gedan)",
                    "ro": "gedan",
                    "en": "gedan",
                },
                "chudan": {
                    "ja": "中段",
                    "ja_en": "中段 (chūdan)",
                    "ro": "chudan",
                    "en": "chudan",
                },
                "jodan": {
                    "ja": "上段",
                    "ja_en": "上段 (jōdan)",
                    "ro": "jodan",
                    "en": "jodan",
                },
            },
            "TURN_MAP": {
                "0": {
                    "ja": "直進",
                    "ja_en": "直進 / straight",
                    "ro": "0",
                    "en": "0",
                },
                "advance": {
                    "ja": "前進",
                    "ja_en": "前進 / advance",
                    "ro": "advance",
                    "en": "advance",
                },
                "left_45": {
                    "ja": "左45°",
                    "ja_en": "左45° / left 45°",
                    "ro": "left 45°",
                    "en": "left 45°",
                },
                "right_45": {
                    "ja": "右45°",
                    "ja_en": "右45° / right 45°",
                    "ro": "right 45°",
                    "en": "right 45°",
                },
                "left_90": {
                    "ja": "左90°",
                    "ja_en": "左90° / left 90°",
                    "ro": "left 90°",
                    "en": "left 90°",
                },
                "right_90": {
                    "ja": "右90°",
                    "ja_en": "右90° / right 90°",
                    "ro": "right 90°",
                    "en": "right 90°",
                },
                "left_135": {
                    "ja": "左135°",
                    "ja_en": "左135° / left 135°",
                    "ro": "left 135°",
                    "en": "left 135°",
                },
                "right_135": {
                    "ja": "右135°",
                    "ja_en": "右135° / right 135°",
                    "ro": "right 135°",
                    "en": "right 135°",
                },
                "left_180": {
                    "ja": "左180°",
                    "ja_en": "左180° / left 180°",
                    "ro": "left 180°",
                    "en": "left 180°",
                },
                "right_180": {
                    "ja": "右180°",
                    "ja_en": "右180° / right 180°",
                    "ro": "right 180°",
                    "en": "right 180°",
                },
                "left_225": {
                    "ja": "左225°",
                    "ja_en": "左225° / left 225°",
                    "ro": "left 225°",
                    "en": "left 225°",
                },
                "right_225": {
                    "ja": "右225°",
                    "ja_en": "右225° / right 225°",
                    "ro": "right 225°",
                    "en": "right 225°",
                },
            },
            "FACING_MAP": {
                "N": {
                    "ja": "北",
                    "ja_en": "北 (N)",
                    "ro": "N",
                    "en": "N",
                },
                "NE": {
                    "ja": "北東",
                    "ja_en": "北東 (NE)",
                    "ro": "NE",
                    "en": "NE",
                },
                "E": {
                    "ja": "東",
                    "ja_en": "東 (E)",
                    "ro": "E",
                    "en": "E",
                },
                "SE": {
                    "ja": "南東",
                    "ja_en": "南東 (SE)",
                    "ro": "SE",
                    "en": "SE",
                },
                "S": {
                    "ja": "南",
                    "ja_en": "南 (S)",
                    "ro": "S",
                    "en": "S",
                },
                "SW": {
                    "ja": "南西",
                    "ja_en": "南西 (SW)",
                    "ro": "SW",
                    "en": "SW",
                },
                "W": {
                    "ja": "西",
                    "ja_en": "西 (W)",
                    "ro": "W",
                    "en": "W",
                },
                "NW": {
                    "ja": "北西",
                    "ja_en": "北西 (NW)",
                    "ro": "NW",
                    "en": "NW",
                },
            },
            "TAG_MAP": {
                "pinan": {"ja": "平安", "ja_en": "pinan"},
                "shitoryu": {"ja": "糸東流", "ja_en": "shitoryu"},
                "extra_kata": {"ja": "追加型", "ja_en": "extra_kata"},
                "kyu_grade": {"ja": "級位", "ja_en": "kyu_grade"},
                "black_belt": {"ja": "有段", "ja_en": "black_belt"},
                "sentei": {"ja": "選定形", "ja_en": "sentei"},
                "shitei": {"ja": "指定形", "ja_en": "shitei"},
                "1st_kyu": {"ja": "一級", "ja_en": "1st_kyu"},
                "2nd_kyu": {"ja": "二級", "ja_en": "2nd_kyu"},
                "3rd_kyu": {"ja": "三級", "ja_en": "3rd_kyu"},
                "4th_kyu": {"ja": "四級", "ja_en": "4th_kyu"},
                "5th_kyu": {"ja": "五級", "ja_en": "5th_kyu"},
                "6th_kyu": {"ja": "六級", "ja_en": "6th_kyu"},
                "7th_kyu": {"ja": "七級", "ja_en": "7th_kyu"},
                "8th_kyu": {"ja": "八級", "ja_en": "8th_kyu"},
                "9th_kyu": {"ja": "九級", "ja_en": "9th_kyu"},
            },
            "CATEGORY_MAP": {
                "block": {
                    "ja": "受け",
                    "ja_en": "受け (Block)",
                    "ro": "Block (受け)",
                    "en": "Block",
                },
                "punch": {
                    "ja": "突き",
                    "ja_en": "突き (Punch)",
                    "ro": "Punch (突き)",
                    "en": "Punch",
                },
                "strike": {
                    "ja": "打ち",
                    "ja_en": "打ち (Strike)",
                    "ro": "Strike (打ち)",
                    "en": "Strike",
                },
                "kick": {
                    "ja": "蹴り",
                    "ja_en": "蹴り (Kick)",
                    "ro": "Kick (蹴り)",
                    "en": "Kick",
                },
                "other": {
                    "ja": "その他",
                    "ja_en": "その他 (Other)",
                    "ro": "Other (その他)",
                    "en": "Other",
                },
            },
        }
    )

    # 7. Setup Output Directories in dist/
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "kata" / "jka").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "kata" / "shitoryu").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "tags").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "static").mkdir(parents=True, exist_ok=True)

    # Copy Static Assets
    for asset in STATIC_DIR.glob("*"):
        if asset.is_file():
            shutil.copy(asset, DIST_DIR / "static" / asset.name)

    # 8. Render Catalog Index & Stats Pages
    print("Rendering HTML pages:")
    index_tpl = env.get_template("index.html")
    index_html = index_tpl.render(
        rel_root="",
        nav_active="catalog",
        jka_25=jka_25,
        jka_extra=jka_extra,
        shitoryu_kata=shitoryu_kata,
        all_tags=all_tags,
    )
    with open(DIST_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    stats_tpl = env.get_template("stats.html")
    stats_html = stats_tpl.render(
        rel_root="",
        nav_active="stats",
        stats=global_stats,
    )
    with open(DIST_DIR / "stats.html", "w", encoding="utf-8") as f:
        f.write(stats_html)

    # 9. Render Individual Kata Pages
    kata_tpl = env.get_template("kata.html")
    for k in tqdm(all_kata, desc="Rendering Kata Pages", unit="page"):
        # Construct tabs for equivalents
        tabs = []
        # Tab 1: Current Kata
        current_style_label = "JKA" if k["style"] == "jka" else "Shito-ryu"
        current_style_ja = "JKA" if k["style"] == "jka" else "糸東流"
        tabs.append(
            {
                "label": f"{current_style_label}: {k['name']}",
                "label_ja": f"{current_style_ja}: {k['kanji']}",
                "label_ja_en": f"{current_style_label}: {k['name']}",
                "label_ro": f"{current_style_label}: {k['name']}",
                "label_en": f"{current_style_label}: {k['name']}",
                "url": f"{k['id']}.html",
                "is_current": True,
            }
        )
        # Tab 2+: Equivalents
        for eq_key in k.get("equivalent_keys", []):
            eq_obj = kata_by_key.get(eq_key)
            if eq_obj:
                eq_style_label = "JKA" if eq_obj["style"] == "jka" else "Shito-ryu"
                eq_style_ja = "JKA" if eq_obj["style"] == "jka" else "糸東流"
                eq_url = f"../../kata/{eq_obj['style']}/{eq_obj['id']}.html"
                tabs.append(
                    {
                        "label": f"{eq_style_label}: {eq_obj['name']}",
                        "label_ja": f"{eq_style_ja}: {eq_obj['kanji']}",
                        "label_ja_en": f"{eq_style_label}: {eq_obj['name']}",
                        "label_ro": f"{eq_style_label}: {eq_obj['name']}",
                        "label_en": f"{eq_style_label}: {eq_obj['name']}",
                        "url": eq_url,
                        "is_current": False,
                    }
                )

        k_html = kata_tpl.render(
            rel_root="../../",
            nav_active="catalog",
            kata=k,
            equivalents_tabs=tabs if len(tabs) > 1 else None,
        )
        out_path = DIST_DIR / "kata" / k["style"] / f"{k['id']}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(k_html)

    # 10. Render Tag Pages
    tag_tpl = env.get_template("tag.html")
    for t in tqdm(all_tags, desc="Rendering Tag Pages", unit="tag"):
        matching = [k for k in all_kata if t in k.get("tags", [])]
        t_html = tag_tpl.render(
            rel_root="../",
            nav_active="catalog",
            tag_name=t,
            matching_kata=matching,
        )
        with open(DIST_DIR / "tags" / f"{t}.html", "w", encoding="utf-8") as f:
            f.write(t_html)

    elapsed = time.perf_counter() - start_time
    print(
        f"\nBuild successfully finished in {elapsed:.3f}s! Generated output at {DIST_DIR}"
    )


if __name__ == "__main__":
    main()
