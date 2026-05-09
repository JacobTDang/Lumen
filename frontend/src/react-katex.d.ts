// react-katex doesn't ship its own .d.ts. Minimal declaration for our usage.
declare module "react-katex" {
  import type { ComponentType } from "react";
  interface KatexProps {
    math: string;
    block?: boolean;
    errorColor?: string;
    renderError?: (error: Error) => React.ReactNode;
    settings?: object;
  }
  export const InlineMath: ComponentType<KatexProps>;
  export const BlockMath: ComponentType<KatexProps>;
}
