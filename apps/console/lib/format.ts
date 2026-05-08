export function shortNumber(value: number) {
  return new Intl.NumberFormat("en", { notation: value > 999 ? "compact" : "standard" }).format(value);
}

export function formatTime(value: string) {
  const date = new Date(value);
  return [
    date.getUTCHours(),
    date.getUTCMinutes(),
    date.getUTCSeconds(),
  ].map((part) => String(part).padStart(2, "0")).join(":");
}

export function formatDateTime(value: string) {
  const date = new Date(value);
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
    date.getUTCMonth()
  ];
  const day = String(date.getUTCDate()).padStart(2, "0");
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(date.getUTCMinutes()).padStart(2, "0");
  return `${month} ${day}, ${hour}:${minute}`;
}

export function riskTone(risk: string): "success" | "warning" | "danger" | "accent" {
  if (risk === "critical") return "danger";
  if (risk === "elevated") return "warning";
  if (risk === "normal") return "success";
  return "accent";
}
