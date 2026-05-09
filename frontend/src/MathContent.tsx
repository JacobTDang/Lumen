// Renders a math step that may contain LaTeX. Heuristic:
// - if the string contains backslash sequences (\int, \frac, etc.) OR
//   $...$ delimiters, attempt KaTeX rendering
// - otherwise fall back to plain text (the parser frequently emits Unicode
//   like ∫₀⁴ x² dx which already looks fine without LaTeX)
//
// Tries to be safe: KaTeX render failures fall back to plain text instead
// of crashing the whole panel.

import React from "react";
import { InlineMath } from "react-katex";
import "katex/dist/katex.min.css";

interface Props {
  text: string;
}

export const MathContent: React.FC<Props> = ({ text }) => {
  // Quick check — does this string look like it has LaTeX?
  const hasLatex = /\\[a-zA-Z]+|\$[^$]+\$/.test(text);

  if (!hasLatex) {
    return <>{text}</>;
  }

  // Strategy: split on $...$ regions, render those as InlineMath, leave
  // the rest as text. This handles mixed content like:
  //   "Step 1: Apply $\int x^2 \, dx = \frac{x^3}{3}$ at the bounds"
  //
  // For backslash-only content like "Step 1: ∫\\int x^2", just render
  // the whole thing as a single InlineMath chunk.
  const dollarRegions = text.split(/(\$[^$]+\$)/);
  if (dollarRegions.length > 1) {
    return (
      <>
        {dollarRegions.map((region, i) => {
          if (region.startsWith("$") && region.endsWith("$")) {
            const math = region.slice(1, -1);
            try {
              return <InlineMath key={i} math={math} />;
            } catch {
              return <span key={i}>{region}</span>;
            }
          }
          return <span key={i}>{region}</span>;
        })}
      </>
    );
  }

  // Pure backslash content — try the whole string as one expression.
  try {
    return <InlineMath math={text} />;
  } catch {
    return <>{text}</>;
  }
};
