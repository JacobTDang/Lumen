import json
import os

from manim import *


def _load_params() -> dict:
    job_id = os.environ.get("MANIM_JOB_ID")
    if job_id:
        temp_dir = os.environ.get("MANIM_TEMP_DIR", os.path.join("media", "temp"))
        params_path = os.path.join(temp_dir, f"{job_id}.json")
        if os.path.exists(params_path):
            with open(params_path) as f:
                return json.load(f)
    return {}


class BubbleSortScene(Scene):
    def construct(self):
        self.camera.background_color = "#0d1117"
        params = _load_params()
        arr = list(params.get("array", [5, 3, 8, 1, 9, 2]))
        n = len(arr)

        cells = self._make_cells(arr)
        row = VGroup(*cells).arrange(RIGHT, buff=0.15).center()
        self.play(FadeIn(row))
        self.wait(0.3)

        for i in range(n):
            for j in range(n - i - 1):
                self.play(
                    cells[j][0].animate.set_fill(YELLOW, opacity=0.7),
                    cells[j + 1][0].animate.set_fill(YELLOW, opacity=0.7),
                    run_time=0.25,
                )

                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    p1 = cells[j].get_center().copy()
                    p2 = cells[j + 1].get_center().copy()
                    self.play(
                        cells[j].animate.move_to(p2),
                        cells[j + 1].animate.move_to(p1),
                        run_time=0.4,
                    )
                    cells[j], cells[j + 1] = cells[j + 1], cells[j]

                self.play(
                    cells[j][0].animate.set_fill(BLUE_E, opacity=0.5),
                    cells[j + 1][0].animate.set_fill(BLUE_E, opacity=0.5),
                    run_time=0.2,
                )

            self.play(cells[n - i - 1][0].animate.set_fill(GREEN_E, opacity=0.7), run_time=0.2)

        self.wait(0.8)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)

    def _make_cells(self, arr: list) -> list:
        cells = []
        for val in arr:
            sq = Square(
                side_length=0.9,
                fill_color=BLUE_E,
                fill_opacity=0.5,
                stroke_color=WHITE,
                stroke_width=2,
            )
            lbl = Text(str(val), font_size=28, color=WHITE)
            cells.append(VGroup(sq, lbl))
        return cells
