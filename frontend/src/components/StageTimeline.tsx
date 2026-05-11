// Stage timeline — visualizes the backend job's stage progression.
//
// Renders a vertical list of stages. The current stage gets a spinner +
// optional progress bar; completed stages get a checkmark; future stages
// are dimmed. Backend stage strings:
//   queued, planning_narrative, building_scenes,
//   rendering_X_of_N, stitching, done, error

import React from "react";
import { Check, Loader2, Circle, AlertCircle } from "lucide-react";
import { C, BODY } from "../theme";

interface Props {
  /** Current backend stage string. Empty/null while waiting for first poll. */
  stage: string | null | undefined;
  /** 0..1 overall progress from backend, used for current-stage bar. */
  progress: number;
  /** Optional error message — shown when stage === "error". */
  error?: string | null;
  /** Whether this is a multi-scene lesson (direct-lesson agent path).
   *  Decides if we show the agent planning stages. */
  hasAgentPlanning?: boolean;
}

interface StageDef {
  key: string;             // stable id
  label: string;           // human-readable
  /** Returns "done" | "active" | "pending" given the current backend stage. */
  stateOf: (currentStage: string, n: number) => "done" | "active" | "pending";
}

function parseRenderingScene(stage: string): { x: number; n: number } | null {
  const m = stage.match(/^rendering_(\d+)_of_(\d+)$/);
  if (!m) return null;
  return { x: parseInt(m[1], 10), n: parseInt(m[2], 10) };
}

// Stage order — earlier stages come first. The state-of helpers compare
// the current stage against this order.
const STAGE_ORDER = [
  "queued",
  "planning_narrative",
  "building_scenes",
  // rendering_X_of_N is matched by prefix
  "rendering",
  "stitching",
  "done",
];

function stageRank(stage: string): number {
  if (stage.startsWith("rendering_")) return STAGE_ORDER.indexOf("rendering");
  return STAGE_ORDER.indexOf(stage);
}

export const StageTimeline: React.FC<Props> = ({
  stage,
  progress,
  error,
  hasAgentPlanning = true,
}) => {
  const current = stage || "queued";
  const currentRank = stageRank(current);
  const sceneInfo = parseRenderingScene(current);

  const stages: StageDef[] = [];
  if (hasAgentPlanning) {
    stages.push({
      key: "planning_narrative",
      label: "Planning the narrative",
      stateOf: (s) =>
        s === "planning_narrative" ? "active"
          : stageRank(s) > stageRank("planning_narrative") ? "done"
          : "pending",
    });
    stages.push({
      key: "building_scenes",
      label: "Building scene visuals",
      stateOf: (s) =>
        s === "building_scenes" ? "active"
          : stageRank(s) > stageRank("building_scenes") ? "done"
          : "pending",
    });
  }
  stages.push({
    key: "rendering",
    label: sceneInfo
      ? `Rendering scene ${sceneInfo.x} of ${sceneInfo.n}`
      : "Rendering",
    stateOf: (s) =>
      s.startsWith("rendering_") || s === "queued" ? "active"
        : stageRank(s) > stageRank("rendering") ? "done"
        : "pending",
  });
  stages.push({
    key: "stitching",
    label: "Stitching the final video",
    stateOf: (s) =>
      s === "stitching" ? "active"
        : stageRank(s) > stageRank("stitching") ? "done"
        : "pending",
  });
  stages.push({
    key: "done",
    label: "Ready",
    stateOf: (s) => (s === "done" ? "done" : "pending"),
  });

  // Special case: error stage breaks the progression
  const isError = current === "error";

  return (
    <div
      style={{
        fontFamily: BODY,
        padding: 20,
        background: C.surface,
        border: `1px solid ${C.borderAlt}`,
        borderRadius: 8,
        maxWidth: 480,
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {stages.map((s) => {
          const state = isError && s.stateOf(STAGE_ORDER[Math.max(0, currentRank)], 0) === "active"
            ? "error" as const
            : s.stateOf(current, 0);

          return (
            <div
              key={s.key}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              {/* Status icon */}
              <div
                style={{
                  width: 20,
                  height: 20,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {state === "done" && (
                  <Check size={16} color={C.ok} strokeWidth={2.5} />
                )}
                {state === "active" && (
                  <Loader2 size={16} color={C.accent} strokeWidth={2.5}
                           className="animate-spin" />
                )}
                {state === "pending" && (
                  <Circle size={10} color={C.textFaint} strokeWidth={2} />
                )}
                {state === "error" && (
                  <AlertCircle size={16} color="#ef4444" strokeWidth={2.5} />
                )}
              </div>

              {/* Label + (optional) progress bar */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    color:
                      state === "done" ? C.text :
                      state === "active" ? C.text :
                      state === "error" ? "#fca5a5" :
                      C.textFaint,
                    fontWeight: state === "active" ? 500 : 400,
                  }}
                >
                  {s.label}
                </div>

                {state === "active" && progress > 0 && progress < 1 && (
                  <div
                    style={{
                      marginTop: 6,
                      height: 3,
                      background: C.borderAlt,
                      borderRadius: 2,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.round(progress * 100)}%`,
                        height: "100%",
                        background: C.accent,
                        transition: "width 0.3s ease-out",
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {isError && error && (
        <div
          style={{
            marginTop: 14,
            padding: 10,
            background: "rgba(239, 68, 68, 0.10)",
            border: "1px solid rgba(239, 68, 68, 0.35)",
            borderRadius: 4,
            color: "#fca5a5",
            fontSize: 12,
            lineHeight: 1.5,
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
};
