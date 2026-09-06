// Event category → clean badge text + readable label
const EVENT_MAP: Record<string, { icon: string; label: string }> = {
  RAIN: { icon: "RAIN", label: "Rain" },
  FLOOD: { icon: "FLD", label: "Flood" },
  WATERLOGGING: { icon: "LOG", label: "Waterlogging" },
  THUNDERSTORM: { icon: "STM", label: "Thunderstorm" },
  LIGHTNING: { icon: "LTG", label: "Lightning" },
  HEATWAVE: { icon: "HEAT", label: "Heatwave" },
  FOG: { icon: "FOG", label: "Fog" },
  DUST_STORM: { icon: "DUST", label: "Dust Storm" },
  STRONG_WIND: { icon: "WIND", label: "Strong Wind" },
  HAILSTORM: { icon: "HAIL", label: "Hailstorm" },
  CYCLONE: { icon: "CYC", label: "Cyclone" },
  OTHER: { icon: "EVT", label: "Weather Event" },
};

export function EventIcon({
  category,
  showLabel = false,
  size = "md",
}: {
  category: string;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
}) {
  const { icon, label } = EVENT_MAP[category?.toUpperCase()] ?? EVENT_MAP.OTHER;
  const sizeClass = { sm: "px-1.5 py-0.5 text-xs", md: "px-2 py-0.5 text-xs font-bold", lg: "px-2.5 py-1 text-sm font-bold" }[size];

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`inline-block rounded bg-blue-900/40 text-blue-300 border border-blue-700/50 ${sizeClass}`}>
        {icon}
      </span>
      {showLabel && <span className="event-label">{label}</span>}
    </span>
  );
}
