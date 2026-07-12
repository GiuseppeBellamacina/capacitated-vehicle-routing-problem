import React from "react";

export function Collapsible({
  expanded,
  children,
}: {
  expanded: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`collapsible${expanded ? " open" : ""}`}>
      <div className="collapsible-inner">{children}</div>
    </div>
  );
}
