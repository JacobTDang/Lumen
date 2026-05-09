// Shared types used across pages and the API client.

export type AnimResult = {
  videoUrl: string;
  status: "ready" | "error";
  error?: string;
};

export interface ParsedAlternative {
  scene: string;
  params: Record<string, any>;
  label: string;
  why?: string;
}

export interface ParsedLessonStep {
  scene: string;
  params: Record<string, any>;
  caption?: string;
}

export interface ParsedProblem {
  domain: "math" | "dsa";
  title: string;
  scene: string;
  params: Record<string, any>;
  explanation: string;
  why_this_pattern: string;
  // DSA-only:
  pseudocode?: string;
  step_lines?: Record<string, number>;
  // Math-only:
  steps?: string[];
  // Both:
  alternatives?: ParsedAlternative[];
  lesson_steps?: ParsedLessonStep[];
}
