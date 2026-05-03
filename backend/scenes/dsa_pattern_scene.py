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
    GridPanel, BinaryTreePanel, RecursionTree, IntervalBars,
    DoublyLinkedListPanel, GraphPanel,
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
        rb = result_box(verdict, font_size=28).to_edge(DOWN, buff=1.75)
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

        rb = result_box(msg, font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(vc)
        self.play(FadeOut(act), FadeIn(rb))
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

        rb = result_box(f"Result: {result}", font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
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
        rb = result_box(f"Best window length: {best_len}", font_size=26).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
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

        rb = result_box(f"Answer: {steps[-1]['M']}", font_size=26).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
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

        # Result strip below input — kept above the result_box zone (buff=1.75)
        result_strip = ArrayStrip([-1] * len(arr),
                                   position=LEFT * 1.5 + DOWN * 1.0,
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

        rb = result_box(f"Result: {result}", font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
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

                rb = result_box(f"Range sum = {step['ans']}", font_size=26).to_edge(DOWN, buff=1.75)
                rb[1].set_color(KEEP)
                self.play(FadeOut(act), FadeIn(rb))

        if algorithm == "build_prefix":
            rb = result_box(f"Built: {result}", font_size=22).to_edge(DOWN, buff=1.75)
            rb[1].set_color(KEEP)
            self.play(FadeOut(act), FadeIn(rb))

        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  KadanesScene — maximum subarray sum
# ===========================================================================

def _kadanes_steps(arr: list) -> tuple:
    """Each step: {i, value, current_sum, max_sum, l, r, kind, action}."""
    steps = []
    if not arr:
        return steps, (0, 0, -1)
    cur = arr[0]
    best = arr[0]
    l = r = best_l = best_r = 0
    steps.append({"i": 0, "value": arr[0], "current_sum": cur, "max_sum": best,
                   "l": l, "r": r, "kind": "init",
                   "action": f"start: cur={cur}, best={best}"})
    for i in range(1, len(arr)):
        v = arr[i]
        if cur + v < v:
            cur = v
            l = i
            kind = "reset"
            action = f"arr[{i}]={v}; cur+v < v → reset cur to {v}, l={i}"
        else:
            cur = cur + v
            kind = "extend"
            action = f"arr[{i}]={v}; extend cur to {cur}"
        r = i
        if cur > best:
            best = cur
            best_l, best_r = l, r
            kind = "new_max"
            action = f"new max! cur={cur}, window=[{best_l}..{best_r}]"
        steps.append({"i": i, "value": v, "current_sum": cur, "max_sum": best,
                       "l": l, "r": r, "kind": kind, "action": action})
    return steps, (best, best_l, best_r)


class KadanesScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr = p.get("array", [-2, 1, -3, 4, -1, 2, 1, -5, 4])
        cap = p.get("caption", "")

        title = Text("Kadane's — Maximum Subarray Sum", font_size=28).to_edge(UP, buff=0.3)
        strip = ArrayStrip(arr, position=UP * 0.5)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices))

        i_ptr = Pointer("i", color=PTR_COLORS["i"]).place_below(strip, 0)
        self.play(FadeIn(i_ptr.vgroup))

        state = StatePanel(anchor=UR, title="State")
        self.play(FadeIn(state.vgroup))
        self.play(*state.anim_set("cur", 0, color=YELLOW),
                  *state.anim_set("max", 0, color=GREEN), run_time=0.3)

        steps, (best, bl, br) = _kadanes_steps(arr)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        prev_best = None
        for step in steps:
            i = step["i"]
            kind = step["kind"]

            self.play(
                i_ptr.anim_move_to(strip, i),
                strip.anim_set_fill(i, HILITE, 0.85),
                run_time=0.35, rate_func=smooth,
            )

            if kind == "reset":
                # current_sum dropped — flash red
                self.play(strip.flash(i, color=REJECT, scale=1.2), run_time=0.2)
            elif kind == "new_max":
                self.play(strip.flash(i, color=KEEP, scale=1.25), run_time=0.25)

            self.play(*state.anim_set("cur", step["current_sum"], color=YELLOW),
                      *state.anim_set("max", step["max_sum"], color=GREEN),
                      run_time=0.25)
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)

            # Color the current best window in green
            if step["kind"] == "new_max":
                for k in range(len(arr)):
                    if step["l"] <= k <= step["r"]:
                        strip.cells[k][0].set_fill(KEEP, opacity=0.6)
                    else:
                        strip.cells[k][0].set_fill(DEFAULT_CELL, opacity=0.5)
            else:
                self.play(strip.anim_set_fill(i, DEFAULT_CELL, 0.55), run_time=0.15)
                # restore best window highlight
                for k in range(step["l"] if False else 0, len(arr)):
                    pass  # let the green from new_max persist

            self.wait(0.2)

        # Final green-window emphasis
        for k in range(len(arr)):
            strip.cells[k][0].set_fill(KEEP if bl <= k <= br else DEFAULT_CELL,
                                        opacity=0.75 if bl <= k <= br else 0.4)
        self.play(*[strip.flash(k, color=KEEP) for k in range(bl, br + 1)],
                  run_time=0.45)

        rb = result_box(f"Max subarray sum = {best}  [{bl}..{br}]",
                        font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  IntervalMergingScene — merge overlapping intervals
# ===========================================================================

def _interval_merging_steps(intervals: list) -> tuple:
    """Each step: {kind: 'sort'|'examine'|'merge'|'emit', ...}."""
    steps = []
    sorted_iv = sorted(range(len(intervals)), key=lambda k: intervals[k][0])
    sorted_pairs = [list(intervals[k]) for k in sorted_iv]
    steps.append({"kind": "sort", "order": sorted_iv,
                   "action": f"sort by start → indices {sorted_iv}"})

    merged = []
    merged_origin = []  # which sorted-position created each merged bar
    for pos, iv in enumerate(sorted_pairs):
        if not merged:
            merged.append(list(iv))
            merged_origin.append(pos)
            steps.append({"kind": "emit", "merged_idx": 0, "src_pos": pos,
                           "interval": list(iv),
                           "action": f"first interval {iv} → start merged"})
            continue
        last = merged[-1]
        if iv[0] <= last[1]:
            new_end = max(last[1], iv[1])
            steps.append({"kind": "merge", "merged_idx": len(merged) - 1,
                           "src_pos": pos, "interval": list(iv),
                           "old_end": last[1], "new_end": new_end,
                           "action": f"{iv} overlaps last; extend end to {new_end}"})
            last[1] = new_end
        else:
            merged.append(list(iv))
            merged_origin.append(pos)
            steps.append({"kind": "emit", "merged_idx": len(merged) - 1,
                           "src_pos": pos, "interval": list(iv),
                           "action": f"{iv} disjoint; emit new merged interval"})
    return steps, merged


class IntervalMergingScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        intervals = p.get("intervals", [[1, 3], [2, 6], [8, 10], [15, 18]])
        cap = p.get("caption", "")

        title = Text("Merge Overlapping Intervals", font_size=28).to_edge(UP, buff=0.3)
        bars = IntervalBars(intervals, position=UP * 0.2)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(bars.vgroup))

        steps, merged = _interval_merging_steps(intervals)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))
        self.wait(0.4)

        for step in steps[1:]:
            kind = step["kind"]
            pos = step["src_pos"]
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            if kind == "emit":
                self.play(bars.anim_set_color(pos, KEEP), run_time=0.3)
            elif kind == "merge":
                anims = bars.anim_merge(step["merged_idx"], pos, step["new_end"])
                self.play(*anims, run_time=0.5)
            self.wait(0.4)

        rb = result_box(f"merged: {merged}", font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  UnionFindScene — disjoint set with parent[] visualization
# ===========================================================================

def _union_find_steps(n: int, operations: list) -> tuple:
    """Operations: ['union 0 1', 'union 2 3', 'find 0', ...]
    Each step: {op, a, b?, parent_before, parent_after, root_a?, root_b?, action, kind}.
    """
    parent = list(range(n))
    steps = []

    def find_root(x):
        path = [x]
        while parent[x] != x:
            x = parent[x]
            path.append(x)
        return x, path

<<<<<<< HEAD
=======
    def _maybe_int(s):
        try:
            return int(s)
        except (ValueError, TypeError):
            return None

>>>>>>> 044ede7 (Connected back end to front end)
    for raw in operations:
        parts = raw.strip().split()
        if not parts:
            continue
        op = parts[0]
        if op == "union" and len(parts) >= 3:
<<<<<<< HEAD
            a = int(parts[1]); b = int(parts[2])
=======
            a = _maybe_int(parts[1]); b = _maybe_int(parts[2])
            if a is None or b is None or not (0 <= a < n) or not (0 <= b < n):
                continue   # skip malformed op silently
>>>>>>> 044ede7 (Connected back end to front end)
            ra, _ = find_root(a)
            rb, _ = find_root(b)
            before = list(parent)
            if ra == rb:
                steps.append({"op": "union", "a": a, "b": b,
                               "ra": ra, "rb": rb, "kind": "noop",
                               "parent_before": before, "parent_after": before,
                               "action": f"union({a},{b}): same root {ra}"})
            else:
                parent[ra] = rb  # naive union: a's root → b's root
                after = list(parent)
                steps.append({"op": "union", "a": a, "b": b,
                               "ra": ra, "rb": rb, "kind": "linked",
                               "parent_before": before, "parent_after": after,
                               "action": f"union({a},{b}): root {ra} → {rb}"})
        elif op == "find" and len(parts) >= 2:
<<<<<<< HEAD
            a = int(parts[1])
=======
            a = _maybe_int(parts[1])
            if a is None or not (0 <= a < n):
                continue
>>>>>>> 044ede7 (Connected back end to front end)
            ra, path = find_root(a)
            steps.append({"op": "find", "a": a, "ra": ra, "kind": "find",
                           "path": path,
                           "parent_before": list(parent), "parent_after": list(parent),
                           "action": f"find({a}) → root {ra}  via path {path}"})
    components = len({find_root(i)[0] for i in range(n)})
    return steps, components


class UnionFindScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        n = int(p.get("n", 6))
        operations = p.get("operations",
                            ["union 0 1", "union 2 3", "union 4 5", "union 1 3", "find 4"])
        cap = p.get("caption", "")

        title = Text("Union-Find — Disjoint Set Forest", font_size=26).to_edge(UP, buff=0.3)
        strip = ArrayStrip(list(range(n)), position=UP * 0.5)
        parent_lbl = Text("parent[]:", font_size=18, color=GRAY).next_to(strip.vgroup, LEFT, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(strip.vgroup), Write(strip.indices), FadeIn(parent_lbl))

        state = StatePanel(anchor=UR, title="UF")
        self.play(FadeIn(state.vgroup))
        self.play(*state.anim_set("components", n, color=KEEP), run_time=0.25)

        steps, components = _union_find_steps(n, operations)
        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        active_arrows = {}  # i -> Arrow

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            kind = step["kind"]

            if kind == "linked":
                ra, rb = step["ra"], step["rb"]
                # Update the parent[] cell visually
                self.play(strip.anim_set_value(ra, rb),
                          strip.anim_set_fill(ra, HILITE, 0.85),
                          run_time=0.4)
                # Draw an arrow from cell ra → cell rb
                arr = Arrow(strip.cell_top(ra) + UP * 0.05,
                            strip.cell_top(rb) + UP * 0.05,
                            color=YELLOW, buff=0.05, stroke_width=3,
                            max_tip_length_to_length_ratio=0.15)
                active_arrows[ra] = arr
                self.play(Create(arr), run_time=0.3)
                self.play(strip.anim_set_fill(ra, KEEP, 0.7), run_time=0.2)
            elif kind == "find":
                # Highlight path of cells
                path = step["path"]
                anims = [strip.anim_set_fill(i, YELLOW, 0.85) for i in path]
                self.play(*anims, run_time=0.3)
                self.play(*[strip.flash(i, color=YELLOW) for i in path], run_time=0.4)
                self.wait(0.2)
                self.play(*[strip.anim_set_fill(i, DEFAULT_CELL, 0.55) for i in path],
                          run_time=0.2)
            elif kind == "noop":
                self.play(strip.flash(step["a"], color=REJECT, scale=1.1), run_time=0.25)

            self.wait(0.25)

        rb = result_box(f"connected components: {components}",
                        font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  LRUCacheScene — hashmap + doubly-linked list
# ===========================================================================

def _lru_cache_steps(operations: list, capacity: int) -> tuple:
    """Operations like 'put 1 100', 'get 1', 'put 2 200'..."""
    steps = []
    order = []          # head -> tail (head = MRU)
    store = {}          # key -> value

    def _to_int(s):
        try:
            return int(s)
        except (ValueError, TypeError):
            return s   # keep as string if not parseable

    for raw in operations:
        parts = raw.strip().split()
        if not parts:
            continue
        op = parts[0]
        if op == "put" and len(parts) >= 3:
            k = _to_int(parts[1]); v = _to_int(parts[2])
            if k in store:
                store[k] = v
                order.remove(k)
                order.insert(0, k)
                steps.append({"op": "put", "kind": "update", "key": k, "val": v,
                               "action": f"put({k},{v}): update + move to head"})
            else:
                evicted = None
                if len(store) >= capacity:
                    evicted = order.pop()
                    store.pop(evicted, None)
                store[k] = v
                order.insert(0, k)
                steps.append({"op": "put", "kind": "insert", "key": k, "val": v,
                               "evicted": evicted,
                               "action": f"put({k},{v})" + (f" — evict {evicted}" if evicted is not None else "")})
        elif op == "get" and len(parts) >= 2:
            k = _to_int(parts[1])
            if k in store:
                order.remove(k); order.insert(0, k)
                steps.append({"op": "get", "kind": "hit", "key": k, "val": store[k],
                               "action": f"get({k}) → {store[k]}  (move to head)"})
            else:
                steps.append({"op": "get", "kind": "miss", "key": k,
                               "action": f"get({k}) → MISS"})
    return steps, {"order": order, "store": dict(store)}


class LRUCacheScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        operations = p.get("operations", ["put 1 100", "put 2 200", "get 1",
                                            "put 3 300", "get 2", "put 4 400"])
        capacity = int(p.get("capacity", 2))
        cap_text = p.get("caption", "")

        title = Text(f"LRU Cache (capacity={capacity})", font_size=28).to_edge(UP, buff=0.3)

        if cap_text:
            show_title_card(self, cap_text)
            self.play(FadeIn(caption_strip(cap_text)), run_time=0.3)

        self.play(Write(title))

        dll = DoublyLinkedListPanel(position=ORIGIN + UP * 0.2)
        self.play(FadeIn(dll.vgroup))

        hmap = HashMapPanel(anchor=UR, title="HashMap")
        self.play(FadeIn(hmap.vgroup))

        steps, _ = _lru_cache_steps(operations, capacity)
        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.25)
            kind = step["kind"]
            k = step["key"]
            if kind == "insert":
                anims = dll.anim_add_to_head(k, step["val"])
                if anims:
                    self.play(*anims, run_time=0.45)
                self.play(*hmap.anim_set(str(k), step["val"]), run_time=0.3)
                if step.get("evicted") is not None:
                    ev = step["evicted"]
                    self.play(*dll.anim_remove(ev), run_time=0.4)
                    self.play(*hmap.anim_delete(str(ev)), run_time=0.3)
            elif kind == "update":
                self.play(*hmap.anim_set(str(k), step["val"]), run_time=0.3)
                self.play(*dll.anim_move_to_head(k), run_time=0.4)
                self.play(*dll.anim_flash(k, color=YELLOW), run_time=0.25)
            elif kind == "hit":
                self.play(*dll.anim_flash(k, color=KEEP), run_time=0.3)
                self.play(*dll.anim_move_to_head(k), run_time=0.4)
                self.play(*hmap.anim_flash(str(k), color=KEEP), run_time=0.3)
            elif kind == "miss":
                self.wait(0.3)
            self.wait(0.25)

        rb = result_box(f"final order (head→tail): {dll.order()}",
                        font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  GridTraversalScene — BFS or DFS on a grid
# ===========================================================================

def _grid_traversal_steps(grid: list, start: list, target: list, algorithm: str) -> tuple:
    """4-connected grid. 0=open, 1=wall."""
    steps = []
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    visited = [[False] * cols for _ in range(rows)]
    parent = {}
    sr, sc = start
    tr, tc = target
    visited[sr][sc] = True
    frontier = [(sr, sc)]
    found = (sr == tr and sc == tc)
    steps.append({"kind": "start", "r": sr, "c": sc,
                   "action": f"start at ({sr},{sc})"})

    def neighbors(r, c):
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and grid[nr][nc] == 0:
                yield nr, nc

    while frontier and not found:
        if algorithm == "bfs":
            r, c = frontier.pop(0)
        else:
            r, c = frontier.pop()
        steps.append({"kind": "visit", "r": r, "c": c,
                       "action": f"visit ({r},{c})"})
        for nr, nc in neighbors(r, c):
            visited[nr][nc] = True
            parent[(nr, nc)] = (r, c)
            frontier.append((nr, nc))
            steps.append({"kind": "enqueue", "r": nr, "c": nc,
                           "from_r": r, "from_c": c,
                           "action": f"discover ({nr},{nc}) from ({r},{c})"})
            if (nr, nc) == (tr, tc):
                found = True
                break

    path = []
    if found:
        cur = (tr, tc)
        while cur != (sr, sc):
            path.append(cur)
            cur = parent.get(cur, (sr, sc))
        path.append((sr, sc))
        path.reverse()
        steps.append({"kind": "path", "cells": path,
                       "action": f"path of length {len(path)}"})
    else:
        steps.append({"kind": "fail", "action": "target unreachable"})
    return steps, path


class GridTraversalScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        grid = p.get("grid", [[0, 0, 1, 0], [0, 0, 0, 0], [1, 0, 1, 0], [0, 0, 0, 0]])
        start = p.get("start", [0, 0])
        target = p.get("target", [3, 3])
        algorithm = p.get("algorithm", "bfs")
        cap = p.get("caption", "")

        title = Text(f"Grid {algorithm.upper()} — ({start[0]},{start[1]}) -> ({target[0]},{target[1]})",
                     font_size=26).to_edge(UP, buff=0.3)

        display = [["·" if c == 0 else "#" for c in row] for row in grid]
        gp = GridPanel(display, position=ORIGIN + DOWN * 0.1)

        for r in range(len(grid)):
            for c in range(len(grid[0])):
                if grid[r][c] == 1:
                    gp.cells[r][c][0].set_fill("#444444", opacity=0.8)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(gp.vgroup))

        steps, path = _grid_traversal_steps(grid, start, target, algorithm)
        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        sr, sc = start; tr, tc = target
        gp.cells[sr][sc][0].set_fill(GREEN, opacity=0.85)
        gp.cells[tr][tc][0].set_fill(RED, opacity=0.5)
        self.wait(0.4)

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.2)
            kind = step["kind"]
            if kind == "visit":
                r, c = step["r"], step["c"]
                if (r, c) != (sr, sc):
                    self.play(gp.anim_set_fill(r, c, "#3a5c8c", 0.85), run_time=0.18)
            elif kind == "enqueue":
                r, c = step["r"], step["c"]
                self.play(gp.anim_set_fill(r, c, HILITE, 0.7), run_time=0.18)
                self.play(gp.flash(r, c, color=HILITE), run_time=0.18)
            elif kind == "path":
                anims = [gp.anim_set_fill(r, c, KEEP, 0.95) for r, c in step["cells"]]
                self.play(LaggedStart(*anims, lag_ratio=0.15), run_time=0.8)
            elif kind == "fail":
                self.wait(0.3)

        rb_msg = f"path: {len(path)} cells" if path else "no path found"
        rb = result_box(rb_msg, font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP if path else REJECT)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  HeapOpsScene — push/pop with sift-up / sift-down
# ===========================================================================

def _heap_ops_steps(operations: list, heap_type: str = "min") -> tuple:
    """Operations: 'push 5', 'push 3', 'pop' ..."""
    steps = []
    heap = []

    def cmp(a, b):
        return (a < b) if heap_type == "min" else (a > b)

    def sift_up(i):
        while i > 0:
            parent = (i - 1) // 2
            if cmp(heap[i], heap[parent]):
                heap[i], heap[parent] = heap[parent], heap[i]
                steps.append({"kind": "swap", "a": i, "b": parent,
                               "snapshot": list(heap),
                               "action": f"sift up: swap idx {i} and {parent}"})
                i = parent
            else:
                break

    def sift_down(i):
        n = len(heap)
        while True:
            l = 2 * i + 1; r = 2 * i + 2
            best = i
            if l < n and cmp(heap[l], heap[best]):
                best = l
            if r < n and cmp(heap[r], heap[best]):
                best = r
            if best == i:
                break
            heap[i], heap[best] = heap[best], heap[i]
            steps.append({"kind": "swap", "a": i, "b": best,
                           "snapshot": list(heap),
                           "action": f"sift down: swap idx {i} and {best}"})
            i = best

<<<<<<< HEAD
=======
    def _maybe_int(s):
        try:
            return int(s)
        except (ValueError, TypeError):
            return None

>>>>>>> 044ede7 (Connected back end to front end)
    for raw in operations:
        parts = raw.strip().split()
        if not parts:
            continue
        op = parts[0]
        if op == "push" and len(parts) >= 2:
<<<<<<< HEAD
            v = int(parts[1])
=======
            v = _maybe_int(parts[1])
            if v is None:
                continue   # skip malformed push silently
>>>>>>> 044ede7 (Connected back end to front end)
            heap.append(v)
            steps.append({"kind": "push", "value": v, "snapshot": list(heap),
                           "action": f"push {v} at index {len(heap) - 1}"})
            sift_up(len(heap) - 1)
        elif op == "pop":
            if not heap:
                continue
            top = heap[0]
            steps.append({"kind": "pop_top", "value": top, "snapshot": list(heap),
                           "action": f"pop top = {top}"})
            last = heap.pop()
            if heap:
                heap[0] = last
                steps.append({"kind": "replace_root", "value": last, "snapshot": list(heap),
                               "action": f"move last ({last}) to root"})
                sift_down(0)
            else:
                steps.append({"kind": "empty", "snapshot": [], "action": "heap empty"})
    return steps, heap


class HeapOpsScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        operations = p.get("operations", ["push 5", "push 3", "push 8",
                                            "push 1", "push 4", "pop", "pop"])
        heap_type = p.get("heap_type", "min")
        cap = p.get("caption", "")

        title = Text(f"{heap_type.capitalize()}-Heap Operations",
                     font_size=28).to_edge(UP, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))

        steps, final = _heap_ops_steps(operations, heap_type)

        max_n = max((len(s.get("snapshot", [])) for s in steps), default=1)
        tree = BinaryTreePanel([0] * max(max_n, 1), position=DOWN * 0.2)
        for n in tree.nodes:
            n.set_opacity(0)
        for _, _, e in tree.edges:
            e.set_opacity(0)
        self.play(FadeIn(tree.vgroup))

        state = StatePanel(anchor=UR, title="Heap")
        self.play(FadeIn(state.vgroup))

        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        prev_snapshot = []
        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.22)
            snap = step.get("snapshot", [])

            anims = []
            for i in range(max_n):
                if i < len(snap):
                    if tree.nodes[i].get_fill_opacity() < 0.5:
                        tree.nodes[i].set_opacity(1)
                        tree.nodes[i][0].set_fill(DEFAULT_CELL, opacity=0.7)
                        anims.append(FadeIn(tree.nodes[i]))
                    if i >= len(prev_snapshot) or prev_snapshot[i] != snap[i]:
                        anims.append(tree.anim_set_value(i, snap[i]))
                else:
                    if tree.nodes[i].get_fill_opacity() > 0.1:
                        anims.append(FadeOut(tree.nodes[i]))
                        tree.nodes[i].set_opacity(0)

            for u, v, e in tree.edges:
                if u < len(snap) and v < len(snap) and e.get_stroke_opacity() < 0.5:
                    e.set_opacity(1)
                    anims.append(FadeIn(e))
                elif (u >= len(snap) or v >= len(snap)) and e.get_stroke_opacity() > 0.1:
                    anims.append(FadeOut(e))
                    e.set_opacity(0)

            if anims:
                self.play(*anims, run_time=0.4)

            kind = step["kind"]
            if kind == "swap":
                a, b = step["a"], step["b"]
                self.play(tree.flash(a, color=YELLOW),
                          tree.flash(b, color=YELLOW), run_time=0.35)
            elif kind == "push":
                self.play(tree.flash(len(snap) - 1, color=KEEP), run_time=0.3)
            elif kind == "pop_top":
                self.play(tree.flash(0, color=REJECT, scale=1.3), run_time=0.35)

            self.play(*state.anim_set("size", len(snap)), run_time=0.18)
            self.wait(0.18)
            prev_snapshot = snap

        rb = result_box(f"final heap: {final}", font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  DP2DScene — fill a 2D DP table with dependencies
# ===========================================================================

def _dp_2d_steps(algorithm: str, input1: str, input2: str) -> tuple:
    """LCS or edit distance or unique paths."""
    steps = []
    if algorithm == "lcs":
        m, n = len(input1), len(input2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if input1[i - 1] == input2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    steps.append({"r": i, "c": j, "value": dp[i][j],
                                   "deps": [(i - 1, j - 1)],
                                   "action": f"match '{input1[i-1]}' -> dp[{i}][{j}] = {dp[i][j]}"})
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
                    pick = (i - 1, j) if dp[i - 1][j] >= dp[i][j - 1] else (i, j - 1)
                    steps.append({"r": i, "c": j, "value": dp[i][j],
                                   "deps": [pick],
                                   "action": f"no match -> dp[{i}][{j}] = max = {dp[i][j]}"})
        return steps, dp, dp[m][n]

    if algorithm == "edit_distance":
        m, n = len(input1), len(input2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
            steps.append({"r": i, "c": 0, "value": i, "deps": [],
                           "action": f"dp[{i}][0] = {i}"})
        for j in range(1, n + 1):
            dp[0][j] = j
            steps.append({"r": 0, "c": j, "value": j, "deps": [],
                           "action": f"dp[0][{j}] = {j}"})
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if input1[i - 1] == input2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                    steps.append({"r": i, "c": j, "value": dp[i][j],
                                   "deps": [(i - 1, j - 1)],
                                   "action": f"match -> carry dp[{i-1}][{j-1}] = {dp[i][j]}"})
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1])
                    steps.append({"r": i, "c": j, "value": dp[i][j],
                                   "deps": [(i - 1, j - 1), (i - 1, j), (i, j - 1)],
                                   "action": f"1 + min(replace,delete,insert) = {dp[i][j]}"})
        return steps, dp, dp[m][n]

    if algorithm == "unique_paths":
        m = max(int(input1) if str(input1).isdigit() else 3, 1)
        n = max(int(input2) if str(input2).isdigit() else 3, 1)
        dp = [[1] * n for _ in range(m)]
        for i in range(m):
            steps.append({"r": i, "c": 0, "value": 1, "deps": [],
                           "action": f"dp[{i}][0] = 1"})
        for j in range(1, n):
            steps.append({"r": 0, "c": j, "value": 1, "deps": [],
                           "action": f"dp[0][{j}] = 1"})
        for i in range(1, m):
            for j in range(1, n):
                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
                steps.append({"r": i, "c": j, "value": dp[i][j],
                               "deps": [(i - 1, j), (i, j - 1)],
                               "action": f"dp[{i}][{j}] = dp[{i-1}][{j}] + dp[{i}][{j-1}] = {dp[i][j]}"})
        return steps, dp, dp[m - 1][n - 1]

    return steps, [[0]], 0


class DP2DScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        algorithm = p.get("algorithm", "lcs")
        input1 = p.get("input1", "abcde")
        input2 = p.get("input2", "ace")
        cap = p.get("caption", "")

        titles = {
            "lcs": f"LCS - '{input1}' vs '{input2}'",
            "edit_distance": f"Edit Distance - '{input1}' -> '{input2}'",
            "unique_paths": f"Unique Paths - {input1}x{input2} grid",
        }
        title = Text(titles.get(algorithm, algorithm), font_size=26).to_edge(UP, buff=0.3)

        if algorithm == "unique_paths":
            m = max(int(input1) if str(input1).isdigit() else 3, 1)
            n = max(int(input2) if str(input2).isdigit() else 3, 1)
            initial = [[0] * n for _ in range(m)]
        else:
            initial = [[0] * (len(input2) + 1) for _ in range(len(input1) + 1)]

        gp = GridPanel(initial, position=DOWN * 0.4)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))
        self.play(FadeIn(gp.vgroup))

        steps, table, answer = _dp_2d_steps(algorithm, input1, input2)
        act = action_text(steps[0]["action"]) if steps else action_text("...")
        self.play(FadeIn(act))

        for step in steps:
            r, c = step["r"], step["c"]
            self.play(Transform(act, action_text(step["action"])), run_time=0.18)
            dep_anims = []
            for dr, dc in step.get("deps", []):
                if 0 <= dr < gp.rows and 0 <= dc < gp.cols:
                    dep_anims.append(gp.anim_set_fill(dr, dc, HILITE, 0.85))
            if dep_anims:
                self.play(*dep_anims, run_time=0.18)
            self.play(gp.anim_set_value(r, c, step["value"]),
                      gp.anim_set_fill(r, c, KEEP, 0.85),
                      run_time=0.28)
            reset = []
            for dr, dc in step.get("deps", []):
                if 0 <= dr < gp.rows and 0 <= dc < gp.cols:
                    reset.append(gp.anim_set_fill(dr, dc, DEFAULT_CELL, 0.55))
            if reset:
                self.play(*reset, run_time=0.15)

        last_r = gp.rows - 1
        last_c = gp.cols - 1
        self.play(gp.flash(last_r, last_c, color=KEEP, scale=1.3), run_time=0.4)

        rb = result_box(f"answer = {answer}", font_size=24).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  BacktrackingSubsetsScene — DFS decision tree
# ===========================================================================

def _backtracking_subsets_steps(arr: list, algorithm: str = "subsets") -> tuple:
    """Each step: {kind: 'enter'|'leaf'|'exit', path, parent_node_id, ...}."""
    steps = []
    results = []

    if algorithm == "subsets":
        # next_node_id is local; emit (parent_id, label) per spawn
        next_id = [1]   # 0 is root
        def dfs(idx, path, parent_id):
            steps.append({"kind": "leaf", "path": list(path), "node_id": parent_id,
                           "action": f"record subset {path}"})
            results.append(list(path))
            for i in range(idx, len(arr)):
                child_id = next_id[0]
                next_id[0] += 1
                steps.append({"kind": "enter", "parent_id": parent_id,
                               "child_id": child_id, "value": arr[i],
                               "path": path + [arr[i]],
                               "action": f"include arr[{i}] = {arr[i]}"})
                dfs(i + 1, path + [arr[i]], child_id)
                steps.append({"kind": "exit", "node_id": child_id,
                               "value": arr[i],
                               "action": f"backtrack: pop {arr[i]}"})
        dfs(0, [], 0)
        return steps, results

    if algorithm == "permutations":
        next_id = [1]
        def dfs(used, path, parent_id):
            if len(path) == len(arr):
                steps.append({"kind": "leaf", "path": list(path), "node_id": parent_id,
                               "action": f"record permutation {path}"})
                results.append(list(path))
                return
            for i in range(len(arr)):
                if used & (1 << i):
                    continue
                child_id = next_id[0]
                next_id[0] += 1
                steps.append({"kind": "enter", "parent_id": parent_id,
                               "child_id": child_id, "value": arr[i],
                               "path": path + [arr[i]],
                               "action": f"choose arr[{i}] = {arr[i]}"})
                dfs(used | (1 << i), path + [arr[i]], child_id)
                steps.append({"kind": "exit", "node_id": child_id,
                               "value": arr[i],
                               "action": f"backtrack: undo {arr[i]}"})
        dfs(0, [], 0)
        return steps, results

    return steps, results


class BacktrackingSubsetsScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr = p.get("array", [1, 2, 3])
        algorithm = p.get("algorithm", "subsets")
        cap = p.get("caption", "")

        title_text = "Backtracking — Subsets" if algorithm == "subsets" else "Backtracking — Permutations"
        title = Text(title_text, font_size=28).to_edge(UP, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))

        rt = RecursionTree(root_label="[]", position=DOWN * 0.4,
                           width=10.0, level_gap=0.85, node_radius=0.30)
        self.play(FadeIn(rt.root))

        # Current path strip on the right
        path_lbl = Text("path: []", font_size=18, color=WHITE).to_corner(UR, buff=0.5)
        self.play(FadeIn(path_lbl))

        steps, results = _backtracking_subsets_steps(arr, algorithm)
        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.2)
            kind = step["kind"]
            if kind == "enter":
                _, anims = rt.anim_spawn_child(step["parent_id"],
                                                str(step["path"]))
                if anims:
                    self.play(*anims, run_time=0.4)
                # Update path label
                new_path = Text(f"path: {step['path']}", font_size=18,
                                 color=YELLOW).to_corner(UR, buff=0.5)
                self.play(Transform(path_lbl, new_path), run_time=0.2)
            elif kind == "leaf":
                if step["node_id"] in rt.nodes:
                    self.play(rt.nodes[step["node_id"]][0].animate.set_fill(KEEP, opacity=0.9),
                              run_time=0.25)
            elif kind == "exit":
                self.wait(0.1)

            self.wait(0.15)

        # Show result count
        rb = result_box(f"{len(results)} {algorithm}: {results[:6]}{'...' if len(results) > 6 else ''}",
                        font_size=20).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  TrieOpsScene — insert + search words
# ===========================================================================

def _trie_ops_steps(words: list, queries: list) -> tuple:
    """Insert each word, then run each query.

    Each insert step emits 'insert_char' for new edges, 'walk' for existing.
    Each query emits 'walk' or 'miss' or 'final_hit'/'final_miss'.
    """
    steps = []
    # Trie as nested dict of {char: child_dict}; '$' marks word-end
    root = {}
    for w in words:
        node = root
        for ch in w:
            kind = "walk" if ch in node else "insert_char"
            steps.append({"kind": kind, "word": w, "char": ch,
                           "action": f"insert '{w}': {kind} on '{ch}'"})
            if ch not in node:
                node[ch] = {}
            node = node[ch]
        node["$"] = True
        steps.append({"kind": "mark_end", "word": w,
                       "action": f"mark end of '{w}'"})

    results = {}
    for q in queries:
        node = root
        ok = True
        for ch in q:
            if ch not in node:
                steps.append({"kind": "miss", "query": q, "char": ch,
                               "action": f"search '{q}': '{ch}' not in trie"})
                ok = False
                break
            steps.append({"kind": "walk", "query": q, "char": ch,
                           "action": f"search '{q}': walk '{ch}'"})
            node = node[ch]
        if ok and node.get("$"):
            results[q] = True
            steps.append({"kind": "final_hit", "query": q,
                           "action": f"'{q}' is a word ✓"})
        elif ok:
            results[q] = False
            steps.append({"kind": "final_miss", "query": q,
                           "action": f"'{q}' prefix exists but no full word"})
        else:
            results[q] = False
    return steps, results


class TrieOpsScene(Scene):
    """Compact trie display: shows nodes as dots and edges as character labels.
    Path of last operation gets highlighted; tree grows over time.
    """
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        words = p.get("words", ["cat", "car", "card", "care"])
        queries = p.get("queries", ["car", "care", "cab"])
        cap = p.get("caption", "")

        title = Text("Trie — Insert + Search", font_size=28).to_edge(UP, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))

        # Build the trie inline as a static layout so we can fade in nodes/edges in order
        # Internal: each node is keyed by its prefix string; root = ""
        root_circle = Circle(radius=0.22, color=WHITE, stroke_width=2,
                              fill_color=DEFAULT_CELL, fill_opacity=0.7)
        root_circle.move_to(UP * 1.6)
        root_label = Text("∅", font_size=14, color=WHITE).move_to(root_circle.get_center())
        root_g = VGroup(root_circle, root_label)
        self.play(FadeIn(root_g))

        # Discover layout: collect all unique prefixes from words, then BFS to assign positions
        prefixes = set([""])
        for w in words:
            for i in range(1, len(w) + 1):
                prefixes.add(w[:i])

        # Build a tree {parent_prefix: [child_prefixes]}
        children = {pre: [] for pre in prefixes}
        for pre in prefixes:
            if pre == "":
                continue
            parent = pre[:-1]
            if pre not in children[parent]:
                children[parent].append(pre)

        # Assign positions: BFS by depth, equally space siblings within parent's x-span
        positions = {"": (0.0, 1.6)}
        x_span = {"": (-5.0, 5.0)}
        depth = {"": 0}
        from collections import deque as _dq
        q = _dq([""])
        while q:
            pre = q.popleft()
            kids = children[pre]
            x_lo, x_hi = x_span[pre]
            for i, k in enumerate(kids):
                slot_w = (x_hi - x_lo) / max(len(kids), 1)
                kx = x_lo + slot_w * (i + 0.5)
                kd = depth[pre] + 1
                ky = 1.6 - kd * 0.85
                positions[k] = (kx, ky)
                x_span[k] = (x_lo + i * slot_w, x_lo + (i + 1) * slot_w)
                depth[k] = kd
                q.append(k)

        # Mobjects: build all nodes and edges (initially invisible)
        node_mobs = {"": root_g}
        edge_mobs = {}    # parent_prefix -> {char: Line}
        char_lbl_mobs = {}
        for pre in prefixes - {""}:
            x, y = positions[pre]
            c = Circle(radius=0.20, color=WHITE, stroke_width=2,
                       fill_color=DEFAULT_CELL, fill_opacity=0.7).move_to([x, y, 0])
            l = Text(pre[-1], font_size=14, color=WHITE).move_to(c.get_center())
            node_mobs[pre] = VGroup(c, l)
            node_mobs[pre].set_opacity(0)
            self.add(node_mobs[pre])

            parent = pre[:-1]
            px, py = positions[parent]
            edge = Line([px, py - 0.20, 0], [x, y + 0.20, 0],
                         color=GRAY, stroke_width=2).set_opacity(0)
            edge_mobs[pre] = edge
            self.add(edge)

        steps, results = _trie_ops_steps(words, queries)
        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        # Track current cursor (start of word being inserted/searched)
        current_prefix = ""
        cursor = Circle(radius=0.30, color=YELLOW, stroke_width=3,
                         fill_opacity=0).move_to(node_mobs[""].get_center())
        self.play(FadeIn(cursor))

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.18)
            kind = step["kind"]

            if kind in ("insert_char", "walk", "miss"):
                # Walk to next prefix (current_prefix + char)
                if kind == "miss":
                    # Don't move cursor; flash red
                    self.play(cursor.animate.set_color(REJECT), run_time=0.2)
                    self.wait(0.2)
                    self.play(cursor.animate.set_color(YELLOW), run_time=0.15)
                    continue
                if "char" in step:
                    next_pref = current_prefix + step["char"]
                    if next_pref in node_mobs:
                        if kind == "insert_char":
                            # Reveal the new node + edge
                            node_mobs[next_pref].set_opacity(1)
                            edge_mobs[next_pref].set_opacity(1)
                            self.play(FadeIn(node_mobs[next_pref]),
                                      Create(edge_mobs[next_pref]),
                                      run_time=0.3)
                        # Move cursor along
                        self.play(cursor.animate.move_to(node_mobs[next_pref].get_center()),
                                  run_time=0.25, rate_func=smooth)
                        current_prefix = next_pref
            elif kind == "mark_end":
                # Reset cursor to root for next word
                self.play(node_mobs[step["word"]][0].animate.set_fill(KEEP, opacity=0.85),
                          run_time=0.25)
                current_prefix = ""
                self.play(cursor.animate.move_to(node_mobs[""].get_center()),
                          run_time=0.25)
            elif kind == "final_hit":
                self.play(cursor.animate.set_color(KEEP), run_time=0.25)
                current_prefix = ""
                self.play(cursor.animate.move_to(node_mobs[""].get_center()),
                          run_time=0.3)
                self.play(cursor.animate.set_color(YELLOW), run_time=0.15)
            elif kind == "final_miss":
                self.play(cursor.animate.set_color(REJECT), run_time=0.25)
                self.wait(0.3)
                current_prefix = ""
                self.play(cursor.animate.move_to(node_mobs[""].get_center()),
                          run_time=0.3)
                self.play(cursor.animate.set_color(YELLOW), run_time=0.15)
            self.wait(0.15)

        rb_text = ", ".join(f"{q}={'✓' if v else '✗'}" for q, v in results.items())
        rb = result_box(rb_text or "no queries", font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(1.0)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  DijkstraScene — shortest paths with priority-queue
# ===========================================================================

def _dijkstra_steps(num_nodes: int, edges: list, source: int) -> tuple:
    """Each edge: [u, v, w]. Undirected graph."""
    import heapq
    INF = float('inf')
    adj = {i: [] for i in range(num_nodes)}
    for e in edges:
        u, v, w = e[0], e[1], (e[2] if len(e) > 2 else 1)
        adj[u].append((v, w))
        adj[v].append((u, w))

    dist = [INF] * num_nodes
    dist[source] = 0
    visited = [False] * num_nodes
    steps = [{"kind": "init", "source": source,
               "action": f"start at node {source}, dist[{source}]=0"}]

    pq = [(0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if visited[u]:
            continue
        visited[u] = True
        steps.append({"kind": "settle", "node": u, "dist": d,
                       "action": f"settle node {u} with dist={d}"})
        for v, w in adj[u]:
            if visited[v]:
                continue
            nd = d + w
            if nd < dist[v]:
                old = dist[v]
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
                steps.append({"kind": "relax", "u": u, "v": v, "old": old, "new": nd,
                               "action": f"relax edge {u}->{v}: {old if old != INF else '∞'} -> {nd}"})
    return steps, dist


class DijkstraScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        num_nodes = int(p.get("num_nodes", 5))
        edges = p.get("edges", [[0, 1, 4], [0, 2, 1], [2, 1, 2],
                                  [1, 3, 1], [2, 3, 5], [3, 4, 3]])
        source = int(p.get("source", 0))
        cap = p.get("caption", "")

        title = Text(f"Dijkstra — shortest paths from {source}", font_size=26).to_edge(UP, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))

        gp = GraphPanel(num_nodes, edges, position=ORIGIN + DOWN * 0.2,
                         radius=2.0, node_radius=0.30)
        self.play(FadeIn(gp.vgroup))

        dist_panel = HashMapPanel(anchor=UR, title="dist[]")
        self.play(FadeIn(dist_panel.vgroup))

        # Initialize all distances as ∞ except source = 0
        for i in range(num_nodes):
            self.play(*dist_panel.anim_set(str(i), "∞" if i != source else "0"),
                      run_time=0.12)

        steps, dist = _dijkstra_steps(num_nodes, edges, source)
        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))
        self.play(gp.anim_set_node_color(source, KEEP, 0.85), run_time=0.3)

        for step in steps[1:]:
            self.play(Transform(act, action_text(step["action"])), run_time=0.2)
            kind = step["kind"]
            if kind == "settle":
                u = step["node"]
                self.play(gp.anim_set_node_color(u, KEEP, 0.95), run_time=0.3)
                self.play(Indicate(gp.nodes[u][0], color=KEEP), run_time=0.3)
            elif kind == "relax":
                u, v, new = step["u"], step["v"], step["new"]
                anim = gp.anim_flash_edge(u, v, color=YELLOW)
                if anim is not None:
                    self.play(anim, run_time=0.3)
                self.play(*dist_panel.anim_set(str(v), new), run_time=0.3)
                self.play(gp.anim_set_node_color(v, HILITE, 0.7), run_time=0.2)
            self.wait(0.15)

        rb_text = " ".join(f"{i}:{('∞' if d == float('inf') else d)}" for i, d in enumerate(dist))
        rb = result_box(rb_text, font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)


# ===========================================================================
#  SegmentTreeScene — range queries
# ===========================================================================

def _segment_tree_steps(arr: list, queries: list) -> tuple:
    """Build a sum-segment-tree over arr, then run range-sum queries."""
    n = len(arr)
    size = 1
    while size < n:
        size *= 2
    tree = [0] * (2 * size)
    for i, v in enumerate(arr):
        tree[size + i] = v
    steps = []
    for i in range(size - 1, 0, -1):
        tree[i] = tree[2 * i] + tree[2 * i + 1]
        steps.append({"kind": "build", "node": i, "value": tree[i],
                       "action": f"tree[{i}] = tree[{2*i}] + tree[{2*i+1}] = {tree[i]}"})

    def query(l, r):
        l += size; r += size + 1
        result = 0
        path = []
        while l < r:
            if l & 1:
                path.append(l); result += tree[l]; l += 1
            if r & 1:
                r -= 1; path.append(r); result += tree[r]
            l //= 2; r //= 2
        return result, path

    results = []
    for ql in queries:
        l, r = ql[0], ql[1]
        res, path = query(l, r)
        results.append(res)
        steps.append({"kind": "query", "l": l, "r": r, "result": res,
                       "path": path,
                       "action": f"sum({l}..{r}) = {res}  (visit nodes {path})"})
    return steps, results, size, tree


class SegmentTreeScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        p = load_params()
        arr = p.get("array", [1, 3, 5, 7, 9, 11])
        queries = p.get("queries", [[1, 3], [0, 5], [2, 4]])
        cap = p.get("caption", "")

        title = Text(f"Segment Tree — range sum queries", font_size=26).to_edge(UP, buff=0.3)

        if cap:
            show_title_card(self, cap)
            self.play(FadeIn(caption_strip(cap)), run_time=0.3)

        self.play(Write(title))

        steps, results, size, tree = _segment_tree_steps(arr, queries)

        # The tree array we display has values in indices 1..2*size-1
        # We'll show only the "useful" range: 1 to size + n - 1
        useful = 2 * size
        # Render tree using BinaryTreePanel — index 0 unused, so prepend 0
        # BinaryTreePanel uses 0-indexed children (i -> 2i+1, 2i+2). We need (i -> 2i, 2i+1).
        # Workaround: treat node 1 as our "root", display values shifted.
        display_vals = [tree[i] if i < len(tree) else 0 for i in range(1, useful)]
        # Pad to a complete tree if needed
        bt = BinaryTreePanel(display_vals, position=DOWN * 0.4 + UP * 0.3,
                              node_radius=0.26, level_gap=0.8)
        # But this primitive uses 2i+1, 2i+2 — different from segment tree's 2i, 2i+1.
        # Simpler: show the input array at the bottom and the tree values as text labels.

        # Show input array
        in_strip = ArrayStrip(arr, position=DOWN * 2.3)
        self.play(FadeIn(in_strip.vgroup), Write(in_strip.indices))

        self.play(FadeIn(bt.vgroup))

        if not steps:
            self.wait(0.5)
            return

        act = action_text(steps[0]["action"])
        self.play(FadeIn(act))

        for step in steps:
            self.play(Transform(act, action_text(step["action"])), run_time=0.2)
            kind = step["kind"]
            if kind == "build":
                n_idx = step["node"] - 1   # display offset
                if 0 <= n_idx < len(bt.nodes):
                    self.play(bt.anim_set_value(n_idx, step["value"]),
                              bt.anim_set_fill(n_idx, KEEP, 0.85), run_time=0.25)
                    self.play(bt.flash(n_idx, color=KEEP), run_time=0.2)
                    self.play(bt.anim_set_fill(n_idx, DEFAULT_CELL, 0.7), run_time=0.15)
            elif kind == "query":
                anims = []
                for n in step["path"]:
                    n_idx = n - 1
                    if 0 <= n_idx < len(bt.nodes):
                        anims.append(bt.anim_set_fill(n_idx, HILITE, 0.85))
                if anims:
                    self.play(*anims, run_time=0.4)
                # Also highlight input range
                for k in range(step["l"], step["r"] + 1):
                    if 0 <= k < len(in_strip.cells):
                        in_strip.cells[k][0].set_fill(KEEP, opacity=0.7)
                self.wait(0.4)
                # Reset
                reset = []
                for n in step["path"]:
                    n_idx = n - 1
                    if 0 <= n_idx < len(bt.nodes):
                        reset.append(bt.anim_set_fill(n_idx, DEFAULT_CELL, 0.7))
                for k in range(step["l"], step["r"] + 1):
                    if 0 <= k < len(in_strip.cells):
                        in_strip.cells[k][0].set_fill(DEFAULT_CELL, opacity=0.55)
                if reset:
                    self.play(*reset, run_time=0.2)

        rb = result_box(f"results: {results}", font_size=22).to_edge(DOWN, buff=1.75)
        rb[1].set_color(KEEP)
        self.play(FadeOut(act), FadeIn(rb))
        self.wait(0.9)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)
