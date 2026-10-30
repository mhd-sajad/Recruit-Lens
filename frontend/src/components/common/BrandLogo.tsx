import React from "react";
import { cn } from "../../lib/utils";

interface BrandLogoProps {
  size?: "sm" | "md" | "lg" | "xl";
  showSubtitle?: boolean;
  className?: string;
  asHeading?: boolean;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  size = "md",
  showSubtitle = true,
  className = "",
  asHeading = false,
}) => {
  // Dimension presets based on design specifications
  let textFontSize = "30px";
  let subFontSize = "9px";
  let subMarginTop = "5px";

  if (size === "sm") {
    textFontSize = "22px";
    subFontSize = "7.5px";
    subMarginTop = "3px";
  } else if (size === "md") {
    // Actual top bar size: 30px
    textFontSize = "30px";
    subFontSize = "9px";
    subMarginTop = "5px";
  } else if (size === "lg") {
    textFontSize = "36px";
    subFontSize = "10px";
    subMarginTop = "6px";
  } else if (size === "xl") {
    // Hero / Showcase size: 44px
    textFontSize = "44px";
    subFontSize = "11px";
    subMarginTop = "8px";
  }

  const innerContent = (
    <div className={cn("rl-logo inline-flex flex-col select-none", className)}>
      <span
        className="rl-logo-text leading-none"
        style={{
          fontFamily: "'Space Grotesk', Inter, -apple-system, sans-serif",
          fontSize: textFontSize,
          letterSpacing: "-0.03em",
        }}
      >
        <span style={{ fontWeight: 500 }} className="text-[#0F172A] dark:text-[#E2E8F0]">
          Recruit{" "}
        </span>
        <span style={{ fontWeight: 700 }} className="text-[#4F46E5] dark:text-[#A5B4FC]">
          Lens
        </span>
        <span style={{ fontWeight: 700, color: "#6366F1" }}>
          .
        </span>
      </span>
      {showSubtitle && (
        <span
          className="rl-logo-sub leading-none uppercase text-[#475569] dark:text-[#94A3B8]"
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: subFontSize,
            letterSpacing: "0.24em",
            marginTop: subMarginTop,
          }}
        >
          EXPLAINABLE HIRING
        </span>
      )}
    </div>
  );

  if (asHeading) {
    return (
      <h1 className="inline-block m-0 p-0" aria-label="Recruit Lens">
        {innerContent}
      </h1>
    );
  }

  return innerContent;
};
