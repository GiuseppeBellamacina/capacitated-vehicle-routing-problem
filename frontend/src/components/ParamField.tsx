import React from "react";

interface ParamFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  type?: "int" | "float";
  step?: number;
  min?: number;
  max?: number;
  tip?: string;
}

export function ParamField({
  label,
  value,
  onChange,
  disabled,
  type = "int",
  step,
  min,
  max,
  tip,
}: ParamFieldProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    if (type === "float") {
      const val = parseFloat(raw);
      onChange(Math.max(min ?? -Infinity, Math.min(max ?? Infinity, val || 0)));
    } else {
      const val = parseInt(raw);
      onChange(Math.max(min ?? -Infinity, Math.min(max ?? Infinity, val || 0)));
    }
  };

  return (
    <div className="param-field">
      <label>
        {tip ? (
          <span className="tooltip param-label-tooltip tooltip-below" data-tip={tip}>
            {label}
            <svg
              className="param-info-icon"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              focusable="false"
            >
              <circle cx="8" cy="8" r="7" />
              <path d="M6.5 6.5C6.5 5.67157 7.17157 5 8 5C8.82843 5 9.5 5.67157 9.5 6.5C9.5 7.32843 8.82843 8 8 8V9.5" />
              <circle cx="8" cy="11.5" r="1.2" fill="currentColor" />
            </svg>
          </span>
        ) : (
          label
        )}
      </label>
      <input
        type="number"
        step={step}
        min={min}
        max={max}
        value={value}
        onChange={handleChange}
        disabled={disabled}
        title={tip}
      />
    </div>
  );
}
