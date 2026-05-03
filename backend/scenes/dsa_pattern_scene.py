"""
Granular DSA pattern scenes that compose primitives.

Each scene:
  - runs the actual algorithm in pure Python (always correct)
  - generates a list of step dicts
  - composes primitives from dsa_primitives.py to animate those steps

No visual code is duplicated across scenes — everything reusable lives in
dsa_primitives.
"""
from collections import deque

import numpy as np
from manim import *

from scenes.dsa_primitives import (
    DEFAULT_CELL, HILITE, KEEP, REJECT, PTR_COLORS, PANEL_BG,
    ArrayStrip, Pointer, HighlightZone, HashMapPanel, StatePanel,
    ComparisonMarker, StackWidget, DependencyArc,
    load_params, show_title_card, caption_strip, result_box, action_text,
)


# ===========================================================================
#  ALGORITHM STEP GENERATORS (pure Python, no Manim imports inside)
# ===========================================================================

# ---------------------------------------------------------------------------
# Two pointers — opposite ends
# ---------------------------------------------------------------------------

def _two_pointers_opposite_steps(arr: list, algorithm: str, target=None) -> tuple:
    """
    Returns (steps: list, result: any).
    Each step: {"L": int, "R": int, "action": str, "match": bool, "kind": str}
    """
    steps = []
    L, R = 0, len(arr) - 1

    if algorithm == "palindrome":
        while L < R:
            if str(arr[L]) == str(arr[R]):
                steps.append({"L": L, "R": R, "match": True,
                               "action": f"'{arr[L]}' == '{arr[R]}'  ✓",
                               "symbol": "==", "kind": "match"})
            else:
                steps.append({"L": L, "R": R, "match": False,
                               "action": f"'{arr[L]}' != '{arr[R]}'  ✗  not a palindrome",
                               "symbol": "!=", "kind": "fail"})
                return steps, False
            L += 1
            R -= 1
        return steps, True

    elif algorithm == "two_sum_sorted":
        tgt = int(target) if target is not None else 0
        while L < R:
            s = arr[L] + arr[R]
            if s == tgt:
                steps.append({"L": L, "R": R, "sum": s, "match": True,
                               "action": f"{arr[L]} + {arr[R]} = {s}  =  target ✓",
                               "symbol": "==", "kind": "match"})
                return steps, (L, R)
            elif s < tgt:
                steps.append({"L": L, "R": R, "sum": s, "match": False,
                               "action": f"{arr[L]} + {arr[R]} = {s}  <  {tgt}, move L right",
                               "symbol": "<", "kind": "advance_l"})
                L += 1
            else:
                steps.append({"L": L, "R": R, "sum": s, "match": False,
                               "action": f"{arr[L]} + {arr[R]} = {s}  >  {tgt}, move R left",
                               "symbol": ">", "kind": "advance_r"})
                R -= 1
        steps.append({"L": L, "R": R, "match": False, "action": "no pair found",
                       "symbol": "!=", "kind": "fail"})
        return steps, None

    elif algorithm == "container_water":
        best = 0
        best_pair = (0, 0)
        while L < R:
            h = min(arr[L], arr[R])
            area = h * (R - L)
            if area > best:
                best = area
                best_pair = (L, R)
            steps.append({"L": L, "R": R, "match": False,
                           "area": area,
                           "action": f"width={R - L}, h={h}, area={area} (best={best})",
                           "symbol": ">", "kind": "compute"})
            if arr[L] < arr[R]:
                L += 1
            else:
                R -= 1
        return steps, best

    elif algorithm == "reverse_array":
        result = list(arr)
        while L < R:
            result[L], result[R] = result[R], result[L]
            steps.append({"L": L, "R": R, "match": True,
                           "action": f"swap {arr[L]} ↔ {arr[R]}",
                           "symbol": "<->", "kind": "swap"})
            L += 1
            R -= 1
        return steps, result

    return steps, None


# ---------------------------------------------------------------------------
# Hashmap iteration
# ---------------------------------------------------------------------------

def _hashmap_iteration_steps(arr: list, algorithm: str, target=None) -> tuple:
    """
    Each step: {"i": int, "action": str, "hashmap_diff": dict, "kind": str, ...}
    hashmap_diff is the operation: {"set": (k, v)} | {"delete": k} | {"flash": k} | {"none": True}
    """
    steps = []

    if algorithm == "frequency_count":
        counts = {}
        for i, v in enumerate(arr):
            new_count = counts.get(str(v), 0) + 1
            counts[str(v)] = new_count
            steps.append({
                "i": i,
                "action": f"see '{v}'  →  count[{v}] = {new_count}",
                "hashmap_diff": {"set": (str(v), new_count)},
                "kind": "increment",
            })
        return steps, counts

    elif algorithm == "two_sum_hashmap":
        tgt = int(target) if target is not None else 0
        seen = {}
        for i, v in enumerate(arr):
            need = tgt - v
            if str(need) in seen:
                steps.append({
                    "i": i,
                    "action": f"see {v}, need {need}  ✓ found at index {seen[str(need)]}",
                    "hashmap_diff": {"flash": str(need)},
                    "kind": "match",
                })
                return steps, (seen[str(need)], i)
            seen[str(v)] = i
            steps.append({
                "i": i,
                "action": f"see {v}, looking for {need}, store {v} → {i}",
                "hashmap_diff": {"set": (str(v), i)},
                "kind": "store",
            })
        return steps, None

    elif algorithm == "anagram_check":
        # Phase 1: count first string. Phase 2: decrement using second string.
        # For visual simplicity, treat arr as a single string and compute self-frequency
        counts = {}
        for i, v in enumerate(arr):
            counts[str(v)] = counts.get(str(v), 0) + 1
            steps.append({
                "i": i,
                "action": f"count '{v}': {counts[str(v)]}",
                "hashmap_diff": {"set": (str(v), counts[str(v)])},
                "kind": "increment",
            })
        return steps, counts

    return steps, None


# ===========================================================================
#  PATTERN SCENES
# ===========================================================================

# ---------------------------------------------------------------------------
# Scene: two_pointers_opposite
# ---------------------------------------------------------------------------

class TwoPointersOppositeScene(Scene):
    """
    L starts left, R starts right, converge inward.
    Algorithms: palindrome, two_sum_sorted, container_water, reverse_array.
    """

    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", ["r", "a", "c", "e", "c", "a", "r"])
        algorithm = p.get("algorithm", "palindrome")
        target    = p.get("target")
        cap       = p.get("caption", "")

        # Title
        titles = {
            "palindrome":      "Two Pointers — Palindrome Check",
            "two_sum_sorted":  f"Two Pointers — Two Sum (target={target})",
            "container_water": "Two Pointers — Container with Most Water",
            "reverse_array":   "Two Pointers — Reverse Array",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        # Strip
        strip = ArrayStrip(arr, position=UP * 0.6)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))
        self.wait(0.3)

        # Pointers
        L_ptr = Pointer("L", color=PTR_COLORS["L"]).place_below(strip, 0)
        R_ptr = Pointer("R", color=PTR_COLORS["R"]).place_below(strip, len(arr) - 1)
        self.play(FadeIn(L_ptr.vgroup), FadeIn(R_ptr.vgroup))

        # Run the algorithm
        steps, result = _two_pointers_opposite_steps(arr, algorithm, target)

        # Action text
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            L, R = step["L"], step["R"]
            kind = step.get("kind", "compute")

            # Highlight the two cells being examined
            highlight_color = HILITE
            self.play(
                strip.anim_set_fill(L, highlight_color, 0.75),
                strip.anim_set_fill(R, highlight_color, 0.75),
                run_time=0.3,
            )

            # Show comparison marker
            sym = step.get("symbol", "?")
            marker = ComparisonMarker.between(strip, L, R, symbol=sym,
                                                color=KEEP if step.get("match") else
                                                      (REJECT if kind == "fail" else HILITE))
            self.play(FadeIn(marker.vgroup), run_time=0.3)

            # Update action
            new_act = action_text(step["action"])
            self.play(Transform(act, new_act), run_time=0.3)

            # Brief pause to absorb
            self.wait(0.4)

            # Fade marker out, settle cells
            if kind == "match":
                self.play(
                    strip.anim_set_fill(L, KEEP, 0.7),
                    strip.anim_set_fill(R, KEEP, 0.7),
                    FadeOut(marker.vgroup),
                    run_time=0.25,
                )
            elif kind == "fail":
                self.play(
                    strip.anim_set_fill(L, REJECT, 0.8),
                    strip.anim_set_fill(R, REJECT, 0.8),
                    FadeOut(marker.vgroup),
                    run_time=0.3,
                )
                break  # palindrome failure stops here
            elif kind in ("advance_l", "advance_r", "compute", "swap"):
                self.play(
                    strip.anim_set_fill(L, DEFAULT_CELL, 0.7),
                    strip.anim_set_fill(R, DEFAULT_CELL, 0.7),
                    FadeOut(marker.vgroup),
                    run_time=0.2,
                )

            # Move pointers to next positions if there's a next step
            idx = steps.index(step)
            if idx + 1 < len(steps):
                next_step = steps[idx + 1]
                self.play(
                    L_ptr.anim_move_to(strip, next_step["L"]),
                    R_ptr.anim_move_to(strip, next_step["R"]),
                    run_time=0.4,
                    rate_func=smooth,
                )

        # Final "click" — if pointers met successfully, indicate both
        if algorithm == "palindrome" and result is True:
            mid = len(arr) // 2
            self.play(strip.flash(mid - 1 if len(arr) % 2 == 0 else mid, color=KEEP))

        # Result
        verdict_map = {
            "palindrome":      ("Palindrome!", KEEP) if result else ("Not a Palindrome", REJECT),
            "two_sum_sorted":  (f"Found pair: indices {result}", KEEP) if result else ("No pair found", REJECT),
            "container_water": (f"Max area = {result}", KEEP),
            "reverse_array":   (f"Reversed: {result}", KEEP),
        }
        verdict, vcolor = verdict_map.get(algorithm, ("Done", KEEP))
        rb = result_box(verdict, font_size=28).to_edge(DOWN, buff=1.0)
        for sub in rb:
            if hasattr(sub, "set_color"):
                pass
        rb[1].set_color(vcolor)
        self.play(FadeIn(rb), run_time=0.4)
        self.play(Indicate(rb, scale_factor=1.05))

        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ---------------------------------------------------------------------------
# Scene: hashmap_iteration
# ---------------------------------------------------------------------------

class HashMapIterationScene(Scene):
    """
    Iterate left to right, updating a hashmap panel.
    Algorithms: frequency_count, two_sum_hashmap, anagram_check.
    """

    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", [2, 7, 11, 15])
        algorithm = p.get("algorithm", "frequency_count")
        target    = p.get("target")
        cap       = p.get("caption", "")

        titles = {
            "frequency_count":  "HashMap — Frequency Count",
            "two_sum_hashmap":  f"HashMap — Two Sum (target={target})",
            "anagram_check":    "HashMap — Anagram Frequencies",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        # Place array left-of-center to leave room for hashmap on the right
        strip = ArrayStrip(arr, position=LEFT * 2.5 + UP * 0.4)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        # HashMap panel on the right
        hmap = HashMapPanel(anchor=UR, title="HashMap")
        self.play(FadeIn(hmap.vgroup))

        # Pointer
        i_ptr = Pointer("i", color=PTR_COLORS["i"]).place_below(strip, 0)
        self.play(FadeIn(i_ptr.vgroup))

        # Run algorithm
        steps, result = _hashmap_iteration_steps(arr, algorithm, target)

        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            i = step["i"]
            kind = step.get("kind", "store")

            # Move pointer + highlight current cell
            self.play(
                i_ptr.anim_move_to(strip, i),
                strip.anim_set_fill(i, HILITE, 0.75),
                run_time=0.4,
                rate_func=smooth,
            )
            self.play(strip.flash(i, color=HILITE, scale=1.18), run_time=0.3)

            # Apply hashmap operation
            diff = step.get("hashmap_diff", {})
            anims = []
            if "set" in diff:
                k, v = diff["set"]
                anims.extend(hmap.anim_set(k, v))
            elif "flash" in diff:
                anims.extend(hmap.anim_flash(diff["flash"], color=KEEP))
            elif "delete" in diff:
                anims.extend(hmap.anim_delete(diff["delete"]))

            if anims:
                self.play(*anims, run_time=0.5)

            # Update action
            self.play(Transform(act, action_text(step["action"])), run_time=0.3)

            # Mark cell appropriately
            if kind == "match":
                self.play(strip.anim_set_fill(i, KEEP, 0.8), run_time=0.25)
                self.wait(0.5)
                break
            else:
                self.play(strip.anim_set_fill(i, DEFAULT_CELL, 0.7), run_time=0.2)

        # Final result
        if algorithm == "two_sum_hashmap":
            if result:
                msg = f"Found indices: {result}"
                vc = KEEP
            else:
                msg = "No pair found"
                vc = REJECT
        elif algorithm == "frequency_count":
            msg = f"Final counts: {len(result)} unique"
            vc = KEEP
        else:
            msg = f"{len(result)} unique characters"
            vc = KEEP

        rb = result_box(msg, font_size=24).to_edge(DOWN, buff=1.0)
        rb[1].set_color(vc)
        self.play(FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)
