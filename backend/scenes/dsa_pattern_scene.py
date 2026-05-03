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


# ===========================================================================
#  TwoPointersSameDirScene — slow/fast pointers both starting from left
# ===========================================================================

def _two_pointers_same_dir_steps(arr: list, algorithm: str) -> tuple:
    """slow/fast pointer steps. Each step: {slow, fast, action, kind}."""
    steps = []
    work = list(arr)

    if algorithm == "remove_duplicates":
        if not work:
            return steps, work
        slow = 0
        for fast in range(1, len(work)):
            steps.append({
                "slow": slow, "fast": fast,
                "action": f"compare arr[{slow}]={work[slow]} vs arr[{fast}]={work[fast]}",
                "kind": "compare",
            })
            if work[fast] != work[slow]:
                slow += 1
                work[slow] = work[fast]
                steps.append({
                    "slow": slow, "fast": fast,
                    "action": f"unique → write to arr[{slow}]={work[fast]}",
                    "kind": "write", "write_value": work[fast],
                })
        return steps, work[:slow + 1]

    elif algorithm == "move_zeros":
        slow = 0
        for fast in range(len(work)):
            if work[fast] != 0:
                if slow != fast:
                    work[slow], work[fast] = work[fast], work[slow]
                    steps.append({
                        "slow": slow, "fast": fast,
                        "action": f"swap arr[{slow}] ↔ arr[{fast}]",
                        "kind": "swap",
                    })
                else:
                    steps.append({
                        "slow": slow, "fast": fast,
                        "action": f"arr[{fast}]={work[fast]} non-zero, in place",
                        "kind": "skip",
                    })
                slow += 1
            else:
                steps.append({
                    "slow": slow, "fast": fast,
                    "action": f"arr[{fast}]=0, advance fast",
                    "kind": "advance_fast",
                })
        return steps, work

    return steps, work


class TwoPointersSameDirScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", [1, 1, 2, 2, 3, 4, 4, 5])
        algorithm = p.get("algorithm", "remove_duplicates")
        cap       = p.get("caption", "")

        titles = {
            "remove_duplicates": "Two Pointers — Remove Duplicates",
            "move_zeros":        "Two Pointers — Move Zeros to End",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        strip = ArrayStrip(arr, position=UP * 0.4)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        slow_p = Pointer("slow", color=PTR_COLORS["slow"], label_size=14).place_below(strip, 0)
        fast_p = Pointer("fast", color=PTR_COLORS["fast"], label_size=14).place_below(strip, 0, extra_down=0.35)
        self.play(FadeIn(slow_p.vgroup), FadeIn(fast_p.vgroup))

        state = StatePanel(anchor=UR, title="State")
        self.play(FadeIn(state.vgroup))
        self.play(*state.anim_set("slow", 0, color=PTR_COLORS["slow"]))
        self.play(*state.anim_set("fast", 0, color=PTR_COLORS["fast"]))

        steps, result = _two_pointers_same_dir_steps(arr, algorithm)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            slow, fast = step["slow"], step["fast"]
            kind = step["kind"]

            self.play(
                slow_p.anim_move_to(strip, slow),
                fast_p.anim_move_to(strip, fast, extra_down=0.35),
                run_time=0.4, rate_func=smooth,
            )
            self.play(*state.anim_set("slow", slow, color=PTR_COLORS["slow"]),
                      *state.anim_set("fast", fast, color=PTR_COLORS["fast"]),
                      run_time=0.25)

            if kind in ("compare", "skip", "advance_fast"):
                self.play(strip.anim_set_fill(fast, HILITE, 0.7), run_time=0.2)
                self.play(Transform(act, action_text(step["action"])), run_time=0.25)
                self.wait(0.3)
                self.play(strip.anim_set_fill(fast, DEFAULT_CELL, 0.7), run_time=0.15)
            elif kind == "write":
                self.play(
                    strip.anim_set_value(slow, step["write_value"]),
                    strip.anim_set_fill(slow, KEEP, 0.85),
                    run_time=0.4,
                )
                self.play(strip.flash(slow, color=KEEP, scale=1.2), run_time=0.3)
                self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            elif kind == "swap":
                self.play(
                    strip.anim_set_fill(slow, HILITE, 0.85),
                    strip.anim_set_fill(fast, HILITE, 0.85),
                    run_time=0.2,
                )
                # swap visuals
                a = arr[slow]; b = arr[fast]
                self.play(
                    strip.anim_set_value(slow, b),
                    strip.anim_set_value(fast, a),
                    run_time=0.4,
                )
                arr[slow], arr[fast] = arr[fast], arr[slow]
                self.play(Transform(act, action_text(step["action"])), run_time=0.25)
                self.play(
                    strip.anim_set_fill(slow, KEEP, 0.7),
                    strip.anim_set_fill(fast, DEFAULT_CELL, 0.7),
                    run_time=0.2,
                )

        rb = result_box(f"Result: {result}", font_size=24).to_edge(DOWN, buff=1.0)
        rb[1].set_color(KEEP)
        self.play(FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  SlidingWindowVariableScene — expanding/contracting window
# ===========================================================================

def _sliding_window_variable_steps(arr: list, algorithm: str, k=None) -> tuple:
    """Each step: {L, R, action, kind, hashmap_diff, length}."""
    steps = []

    if algorithm == "longest_no_repeat":
        seen = {}
        L = 0
        best = 0
        best_window = (0, -1)
        for R in range(len(arr)):
            ch = str(arr[R])
            steps.append({
                "L": L, "R": R, "kind": "expand",
                "action": f"expand R: include '{ch}'",
                "hashmap_diff": {"set": (ch, 1)} if ch not in seen or seen[ch] < L else {"set": (ch, seen.get(ch, 0) + 1)},
            })
            if ch in seen and seen[ch] >= L:
                # shrink
                while seen.get(ch, -1) >= L:
                    L_ch = str(arr[L])
                    L += 1
                    steps.append({
                        "L": L, "R": R, "kind": "shrink",
                        "action": f"duplicate '{ch}', shrink L past '{L_ch}'",
                        "hashmap_diff": {"delete": L_ch},
                    })
            seen[ch] = R
            length = R - L + 1
            if length > best:
                best = length
                best_window = (L, R)
                steps.append({
                    "L": L, "R": R, "kind": "best",
                    "action": f"new best length = {length}",
                    "hashmap_diff": {"flash": ch},
                    "length": length,
                })
        return steps, (best, best_window)

    elif algorithm == "longest_at_most_k_distinct":
        kk = int(k) if k else 2
        counts = {}
        L = 0
        best = 0
        for R in range(len(arr)):
            ch = str(arr[R])
            counts[ch] = counts.get(ch, 0) + 1
            steps.append({
                "L": L, "R": R, "kind": "expand",
                "action": f"add '{ch}', distinct={len(counts)}",
                "hashmap_diff": {"set": (ch, counts[ch])},
            })
            while len(counts) > kk:
                L_ch = str(arr[L])
                counts[L_ch] -= 1
                if counts[L_ch] == 0:
                    del counts[L_ch]
                    diff = {"delete": L_ch}
                else:
                    diff = {"set": (L_ch, counts[L_ch])}
                L += 1
                steps.append({
                    "L": L, "R": R, "kind": "shrink",
                    "action": f"too many distinct, shrink L past '{L_ch}'",
                    "hashmap_diff": diff,
                })
            length = R - L + 1
            if length > best:
                best = length
                steps.append({
                    "L": L, "R": R, "kind": "best",
                    "action": f"best length so far = {length}",
                    "hashmap_diff": {"none": True}, "length": length,
                })
        return steps, best

    return steps, None


class SlidingWindowVariableScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", ["a", "b", "c", "a", "b", "c", "b", "b"])
        algorithm = p.get("algorithm", "longest_no_repeat")
        k         = p.get("k")
        cap       = p.get("caption", "")

        titles = {
            "longest_no_repeat":         "Sliding Window — Longest Without Repeating",
            "longest_at_most_k_distinct": f"Sliding Window — At Most {k or 2} Distinct",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        strip = ArrayStrip(arr, position=LEFT * 2.0 + UP * 0.4)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        zone = HighlightZone(strip, 0, 0, color=YELLOW)
        L_ptr = Pointer("L", color=PTR_COLORS["L"]).place_below(strip, 0)
        R_ptr = Pointer("R", color=PTR_COLORS["R"]).place_below(strip, 0, extra_down=0.35)
        self.play(Create(zone.rect), FadeIn(L_ptr.vgroup), FadeIn(R_ptr.vgroup))

        hmap = HashMapPanel(anchor=UR, title="Counts")
        self.play(FadeIn(hmap.vgroup))

        steps, result = _sliding_window_variable_steps(arr, algorithm, k)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            L, R = step["L"], step["R"]
            kind = step["kind"]

            self.play(
                zone.anim_to(L, R),
                L_ptr.anim_move_to(strip, L),
                R_ptr.anim_move_to(strip, R, extra_down=0.35),
                run_time=0.4, rate_func=smooth,
            )

            for i in range(len(arr)):
                strip.cells[i][0].set_fill(DEFAULT_CELL, opacity=0.5)
            for i in range(L, R + 1):
                strip.cells[i][0].set_fill(YELLOW, opacity=0.55)
            if kind == "best":
                for i in range(L, R + 1):
                    strip.cells[i][0].set_fill(KEEP, opacity=0.65)

            diff = step.get("hashmap_diff", {})
            anims = []
            if "set" in diff:
                anims.extend(hmap.anim_set(*diff["set"]))
            elif "delete" in diff:
                anims.extend(hmap.anim_delete(diff["delete"]))
            elif "flash" in diff:
                anims.extend(hmap.anim_flash(diff["flash"], color=KEEP))

            if anims:
                self.play(*anims, run_time=0.4)
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            self.wait(0.25)

        if isinstance(result, tuple):
            best_len = result[0]
        else:
            best_len = result
        rb = result_box(f"Best window length: {best_len}", font_size=26).to_edge(DOWN, buff=1.0)
        rb[1].set_color(KEEP)
        self.play(FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  BinarySearchIndexScene — L/M/R on sorted array
# ===========================================================================

def _binary_search_index_steps(arr: list, algorithm: str, target: int) -> tuple:
    """L/M/R steps. {L, R, M, action, kind, found}."""
    steps = []
    L, R = 0, len(arr) - 1
    found = -1

    if algorithm == "find_target":
        while L <= R:
            M = (L + R) // 2
            steps.append({"L": L, "R": R, "M": M,
                           "action": f"check arr[{M}]={arr[M]} vs {target}",
                           "kind": "compare"})
            if arr[M] == target:
                steps.append({"L": L, "R": R, "M": M,
                               "action": f"arr[{M}]={target} ✓ found at index {M}",
                               "kind": "match", "found": True})
                return steps, M
            elif arr[M] < target:
                steps.append({"L": L, "R": R, "M": M,
                               "action": f"arr[{M}]={arr[M]} < {target}, go right",
                               "kind": "go_right"})
                L = M + 1
            else:
                steps.append({"L": L, "R": R, "M": M,
                               "action": f"arr[{M}]={arr[M]} > {target}, go left",
                               "kind": "go_left"})
                R = M - 1
        steps.append({"L": L, "R": R, "M": -1,
                       "action": f"{target} not found", "kind": "not_found"})
        return steps, -1

    elif algorithm == "first_occurrence":
        while L <= R:
            M = (L + R) // 2
            steps.append({"L": L, "R": R, "M": M,
                           "action": f"check arr[{M}]={arr[M]} vs {target}",
                           "kind": "compare"})
            if arr[M] >= target:
                if arr[M] == target:
                    found = M
                R = M - 1
                steps.append({"L": L, "R": R, "M": M,
                               "action": f"arr[{M}]>={target}, search left for first",
                               "kind": "go_left"})
            else:
                L = M + 1
                steps.append({"L": L, "R": R, "M": M,
                               "action": f"arr[{M}]<{target}, go right",
                               "kind": "go_right"})
        if found >= 0:
            steps.append({"L": L, "R": R, "M": found,
                           "action": f"first {target} at index {found}",
                           "kind": "match", "found": True})
        return steps, found

    return steps, -1


class BinarySearchIndexScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", [1, 3, 5, 7, 9, 11, 13, 15])
        algorithm = p.get("algorithm", "find_target")
        target    = int(p.get("target", 7))
        cap       = p.get("caption", "")

        titles = {
            "find_target":      f"Binary Search — find {target}",
            "first_occurrence": f"Binary Search — first occurrence of {target}",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        strip = ArrayStrip(arr, position=UP * 0.6)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        L_p = Pointer("L", color=PTR_COLORS["L"]).place_below(strip, 0)
        R_p = Pointer("R", color=PTR_COLORS["R"]).place_below(strip, len(arr) - 1)
        M_p = Pointer("M", color=PTR_COLORS["M"]).place_below(strip, len(arr) // 2, extra_down=0.35)
        self.play(FadeIn(L_p.vgroup), FadeIn(R_p.vgroup), FadeIn(M_p.vgroup))

        steps, _ = _binary_search_index_steps(arr, algorithm, target)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            L, R, M = step["L"], step["R"], step["M"]
            kind = step["kind"]

            anims = [L_p.anim_move_to(strip, L), R_p.anim_move_to(strip, R)]
            if M >= 0:
                anims.append(M_p.anim_move_to(strip, M, extra_down=0.35))
            self.play(*anims, run_time=0.4, rate_func=smooth)

            if M >= 0:
                self.play(strip.anim_set_fill(M, HILITE, 0.85), run_time=0.25)
                self.play(strip.flash(M, color=HILITE, scale=1.2), run_time=0.25)

            if kind == "match":
                self.play(strip.anim_set_fill(M, KEEP, 0.85))
            elif kind in ("go_right", "go_left"):
                # dim out the eliminated half
                eliminated = list(range(0, L)) + list(range(R + 1, len(arr)))
                if eliminated:
                    self.play(*[strip.anim_set_fill(i, DEFAULT_CELL, 0.25)
                                for i in eliminated], run_time=0.2)
                if M >= 0:
                    self.play(strip.anim_set_fill(M, DEFAULT_CELL, 0.7), run_time=0.15)

            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            self.wait(0.3)

        self.wait(0.6)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  BinarySearchAnswerScene — search the answer space
# ===========================================================================

def _binary_search_answer_steps(min_v: int, max_v: int, true_at: int) -> list:
    """Find smallest v in [min_v, max_v] such that predicate(v) is True.
       'predicate(v) = True' iff v >= true_at."""
    steps = []
    L, R = min_v, max_v
    while L < R:
        M = (L + R) // 2
        is_true = M >= true_at
        steps.append({"L": L, "R": R, "M": M, "predicate": is_true,
                       "action": f"predicate({M}) = {is_true}"})
        if is_true:
            R = M
        else:
            L = M + 1
    steps.append({"L": L, "R": R, "M": L, "predicate": True,
                   "action": f"smallest valid value: {L}",
                   "found": True})
    return steps


class BinarySearchAnswerScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        min_v   = int(p.get("min_value", 1))
        max_v   = int(p.get("max_value", 16))
        true_at = int(p.get("true_at", 7))
        plabel  = p.get("predicate_label", "feasible(x)")
        cap     = p.get("caption", "")

        title = Text("Binary Search on Answer Space", font_size=28).to_edge(UP, buff=0.3)
        # Use a virtual array of values [min_v..max_v]
        values = list(range(min_v, max_v + 1))
        strip = ArrayStrip(values, position=UP * 0.4)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        L_p = Pointer("L", color=PTR_COLORS["L"]).place_below(strip, 0)
        R_p = Pointer("R", color=PTR_COLORS["R"]).place_below(strip, len(values) - 1)
        M_p = Pointer("M", color=PTR_COLORS["M"]).place_below(strip, len(values) // 2, extra_down=0.35)
        self.play(FadeIn(L_p.vgroup), FadeIn(R_p.vgroup), FadeIn(M_p.vgroup))

        state = StatePanel(anchor=UR, title=plabel)
        self.play(FadeIn(state.vgroup))

        steps = _binary_search_answer_steps(min_v, max_v, true_at)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            L_idx = step["L"] - min_v
            R_idx = step["R"] - min_v
            M_idx = step["M"] - min_v
            pred  = step["predicate"]

            self.play(
                L_p.anim_move_to(strip, L_idx),
                R_p.anim_move_to(strip, R_idx),
                M_p.anim_move_to(strip, M_idx, extra_down=0.35),
                run_time=0.4, rate_func=smooth,
            )
            self.play(strip.anim_set_fill(M_idx, HILITE, 0.85), run_time=0.2)
            self.play(*state.anim_set("predicate", "True" if pred else "False",
                                       color=KEEP if pred else REJECT),
                      run_time=0.25)
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            self.wait(0.4)

            # Dim eliminated cells
            for i in range(len(values)):
                if i < L_idx or i > R_idx:
                    strip.cells[i][0].set_fill(DEFAULT_CELL, opacity=0.18)

        # Final answer
        ans_idx = steps[-1]["M"] - min_v
        self.play(strip.anim_set_fill(ans_idx, KEEP, 0.95))
        self.play(strip.flash(ans_idx, color=KEEP, scale=1.3))

        rb = result_box(f"Answer: {steps[-1]['M']}", font_size=26).to_edge(DOWN, buff=1.0)
        rb[1].set_color(KEEP)
        self.play(FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  MonotonicStackScene — stack maintains monotonic invariant
# ===========================================================================

def _monotonic_stack_steps(arr: list, monotone: str = "decreasing") -> tuple:
    """Returns (steps, result_array). Each step:
       {i, value, action, kind, popped: list, push: bool, stack_after: list}"""
    steps = []
    stack = []  # of indices
    result = [-1] * len(arr)  # next greater element

    for i, v in enumerate(arr):
        popped = []
        if monotone == "decreasing":
            while stack and arr[stack[-1]] < v:
                p = stack.pop()
                popped.append(p)
                result[p] = v
        else:
            while stack and arr[stack[-1]] > v:
                p = stack.pop()
                popped.append(p)
                result[p] = v

        for p in popped:
            steps.append({
                "i": i, "value": v, "kind": "pop",
                "popped_idx": p, "popped_val": arr[p],
                "stack_after": list(stack),
                "action": f"arr[{i}]={v} > arr[{p}]={arr[p]}, pop and resolve {arr[p]}",
            })

        stack.append(i)
        steps.append({
            "i": i, "value": v, "kind": "push",
            "stack_after": list(stack),
            "action": f"push {v} onto stack",
        })

    return steps, result


class MonotonicStackScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", [2, 1, 5, 6, 2, 3])
        algorithm = p.get("algorithm", "next_greater")
        monotone  = p.get("monotone", "decreasing")
        cap       = p.get("caption", "")

        titles = {
            "next_greater":        "Monotonic Stack — Next Greater Element",
            "daily_temperatures":  "Monotonic Stack — Daily Temperatures",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        strip = ArrayStrip(arr, position=LEFT * 1.5 + UP * 0.5)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        i_ptr = Pointer("i", color=PTR_COLORS["i"]).place_below(strip, 0)
        self.play(FadeIn(i_ptr.vgroup))

        # Stack on the right
        stack_pos = RIGHT * 4 + DOWN * 0.5
        stack_w = StackWidget(position=stack_pos, max_visible=6, cell_w=1.0,
                              title="Stack (idx)")
        self.play(FadeIn(stack_w.vgroup))

        # Result strip below input
        result_strip = ArrayStrip([-1] * len(arr),
                                   position=LEFT * 1.5 + DOWN * 1.8,
                                   with_indices=False)
        result_label = Text("result:", font_size=18, color=GRAY).next_to(result_strip.vgroup, LEFT, buff=0.3)
        self.play(FadeIn(result_strip.vgroup), FadeIn(result_label))

        steps, result = _monotonic_stack_steps(arr, monotone)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            i = step["i"]
            kind = step["kind"]

            self.play(i_ptr.anim_move_to(strip, i), run_time=0.3, rate_func=smooth)
            self.play(strip.anim_set_fill(i, HILITE, 0.7), run_time=0.2)

            if kind == "pop":
                p = step["popped_idx"]
                v = step["value"]
                # Update result strip cell
                self.play(strip.flash(p, color=REJECT, scale=1.2), run_time=0.25)
                val, anims = stack_w.anim_pop()
                if anims:
                    self.play(*anims, run_time=0.4)
                self.play(
                    result_strip.anim_set_value(p, v),
                    result_strip.anim_set_fill(p, KEEP, 0.7),
                    run_time=0.3,
                )
            elif kind == "push":
                _, anims = stack_w.anim_push(i, color=BLUE_D)
                if anims:
                    self.play(*anims, run_time=0.4)

            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            self.wait(0.2)

        rb = result_box(f"Result: {result}", font_size=22).to_edge(DOWN, buff=1.0)
        rb[1].set_color(KEEP)
        self.play(FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  PrefixSumScene — cumulative sum overlay
# ===========================================================================

def _prefix_sum_steps(arr: list, algorithm: str, query_range=None, target=None) -> tuple:
    """Steps for building/querying a prefix sum array."""
    steps = []
    prefix = [0] * (len(arr) + 1)

    # Always build the prefix array first
    for i, v in enumerate(arr):
        prefix[i + 1] = prefix[i] + v
        steps.append({
            "i": i + 1, "value": prefix[i + 1], "deps": [i, i + 1],
            "kind": "build",
            "action": f"prefix[{i+1}] = prefix[{i}] + arr[{i}] = {prefix[i]} + {v} = {prefix[i+1]}",
        })

    if algorithm == "build_prefix":
        return steps, prefix

    if algorithm == "range_sum_query":
        l, r = query_range or [0, len(arr) - 1]
        ans = prefix[r + 1] - prefix[l]
        steps.append({
            "kind": "query", "l": l, "r": r, "ans": ans,
            "action": f"sum({l}..{r}) = prefix[{r+1}] - prefix[{l}] = {prefix[r+1]} - {prefix[l]} = {ans}",
        })
        return steps, ans

    return steps, prefix


class PrefixSumScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr       = p.get("array", [3, 1, 4, 1, 5, 9, 2])
        algorithm = p.get("algorithm", "build_prefix")
        query_range = p.get("query_range")
        cap       = p.get("caption", "")

        titles = {
            "build_prefix":      "Prefix Sum — Build Cumulative Array",
            "range_sum_query":   f"Prefix Sum — Range Query [{query_range}]" if query_range else "Prefix Sum — Range Query",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=28).to_edge(UP, buff=0.3)

        # Input array on top
        in_strip = ArrayStrip(arr, position=UP * 1.4)
        in_lbl = Text("arr:", font_size=18, color=GRAY).next_to(in_strip.vgroup, LEFT, buff=0.25)

        # Prefix array on bottom (length n+1)
        prefix_init = [0] * (len(arr) + 1)
        pre_strip = ArrayStrip(prefix_init, position=DOWN * 0.6)
        pre_lbl = Text("prefix:", font_size=18, color=GRAY).next_to(pre_strip.vgroup, LEFT, buff=0.25)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(in_strip.vgroup), Write(in_strip.indices), FadeIn(in_lbl))
        self.play(FadeIn(pre_strip.vgroup), Write(pre_strip.indices), FadeIn(pre_lbl))

        steps, result = _prefix_sum_steps(arr, algorithm, query_range)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            kind = step["kind"]

            if kind == "build":
                i = step["i"]   # index into prefix (1..n)
                # Highlight prefix[i-1] (dep) and arr[i-1] (input)
                self.play(
                    pre_strip.anim_set_fill(i - 1, HILITE, 0.7),
                    in_strip.anim_set_fill(i - 1, HILITE, 0.7),
                    run_time=0.25,
                )
                # Update prefix[i]
                self.play(
                    pre_strip.anim_set_value(i, step["value"]),
                    pre_strip.anim_set_fill(i, KEEP, 0.85),
                    run_time=0.4,
                )
                self.play(pre_strip.flash(i, color=KEEP, scale=1.18), run_time=0.25)
                self.play(Transform(act, action_text(step["action"])), run_time=0.25)
                # Reset
                self.play(
                    pre_strip.anim_set_fill(i - 1, DEFAULT_CELL, 0.7),
                    in_strip.anim_set_fill(i - 1, DEFAULT_CELL, 0.7),
                    pre_strip.anim_set_fill(i, DEFAULT_CELL, 0.7),
                    run_time=0.2,
                )

            elif kind == "query":
                l, r = step["l"], step["r"]
                # Highlight prefix[r+1] and prefix[l] simultaneously
                self.play(
                    pre_strip.anim_set_fill(r + 1, HILITE, 0.85),
                    pre_strip.anim_set_fill(l, REJECT, 0.85),
                    run_time=0.3,
                )
                # Highlight the input range too
                for i in range(l, r + 1):
                    in_strip.cells[i][0].set_fill(KEEP, opacity=0.6)
                self.play(*[in_strip.flash(i, color=KEEP, scale=1.1) for i in range(l, r + 1)],
                          run_time=0.4)
                self.play(Transform(act, action_text(step["action"])), run_time=0.3)

                rb = result_box(f"Range sum = {step['ans']}", font_size=26).to_edge(DOWN, buff=1.0)
                rb[1].set_color(KEEP)
                self.play(FadeIn(rb))

        if algorithm == "build_prefix":
            rb = result_box(f"Built: {result}", font_size=22).to_edge(DOWN, buff=1.0)
            rb[1].set_color(KEEP)
            self.play(FadeIn(rb))

        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)
