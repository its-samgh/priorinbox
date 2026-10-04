export const number = (value: number | null | undefined, suffix = "") =>
  value == null
    ? "—"
    : `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`;
