// EmbedPage — minimal chrome rendering of a shared lesson, suitable for
// <iframe src="/embed/<shareCode>"> on any external site.
//
// Mounted by App.tsx when window.location.pathname starts with "/embed/".
// Skips the sidebar, the notes editor, everything. Just the video + title.

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { C, SANS, BODY } from "../theme";
import { flaskBase } from "../lib/api";
import type { ParsedProblem } from "../types";

interface Props {
  shareCode: string;
}

type EmbedState =
  | { kind: "loading" }
  | { kind: "ready"; parsed: ParsedProblem; videoUrl: string }
  | { kind: "error"; message: string };

const EmbedPage: React.FC<Props> = ({ shareCode }) => {
  const [state, setState] = useState<EmbedState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${flaskBase()}/api/share/${shareCode}`);
        if (!res.ok) {
          throw new Error(`share not found (${res.status})`);
        }
        const { parsed } = await res.json();
        if (!parsed || !parsed.scene) {
          throw new Error("share payload is empty");
        }
        // The share endpoint stores the parsed object; the video URL is on
        // the parsed object only if a saved-render share was used. For agent
        // shares we'd need to re-render. For now, accept whichever URL we
        // find on the payload.
        const videoUrl = parsed.videoUrl || parsed.url;
        if (!videoUrl) {
          throw new Error("no video URL stored in this share");
        }
        if (!cancelled) {
          setState({ kind: "ready", parsed, videoUrl });
        }
      } catch (e) {
        if (!cancelled) {
          setState({
            kind: "error",
            message: e instanceof Error ? e.message : "failed to load",
          });
        }
      }
    })();
    return () => { cancelled = true; };
  }, [shareCode]);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: C.bg,
        color: C.text,
        fontFamily: BODY,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {state.kind === "loading" && (
        <div style={{
          flex: 1, display: "flex", alignItems: "center",
          justifyContent: "center", flexDirection: "column", gap: 12,
        }}>
          <Loader2 size={24} className="animate-spin" color={C.textMuted} strokeWidth={1.5} />
          <span style={{ color: C.textMuted, fontSize: 13 }}>Loading lesson…</span>
        </div>
      )}

      {state.kind === "error" && (
        <div style={{
          flex: 1, display: "flex", alignItems: "center",
          justifyContent: "center", flexDirection: "column", gap: 8,
        }}>
          <div style={{ fontSize: 14, color: "#fca5a5" }}>Lesson unavailable</div>
          <div style={{ fontSize: 12, color: C.textFaint }}>{state.message}</div>
        </div>
      )}

      {state.kind === "ready" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.25 }}
          style={{ flex: 1, display: "flex", flexDirection: "column" }}
        >
          <header style={{
            padding: "10px 16px",
            borderBottom: `1px solid ${C.borderAlt}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}>
            <div style={{
              fontFamily: SANS,
              fontSize: 14,
              fontWeight: 600,
              color: C.text,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {state.parsed.title || state.parsed.scene}
            </div>
            <a
              href="/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: 11,
                color: C.textFaint,
                textDecoration: "none",
                opacity: 0.7,
              }}
            >
              made with Lumen ↗
            </a>
          </header>
          <div style={{
            flex: 1,
            background: "#0d1117",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}>
            <video
              src={state.videoUrl}
              autoPlay
              controls
              loop
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
              }}
            />
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default EmbedPage;
