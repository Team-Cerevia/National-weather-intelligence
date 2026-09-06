// Event category → emoji icon + readable label
const EVENT_MAP: Record<string, { icon: string; label: string }> = {
  RAIN: { icon: "🌧️", label: "Rain" },
  FLOOD: { icon: "🌊", label: "Flood" },
  WATERLOGGING: { icon: "💧", label: "Waterlogging" },
  THUNDERSTORM: { icon: "⛈️", label: "Thunderstorm" },
  LIGHTNING: { icon: "⚡", label: "Lightning" },
  HEATWAVE: { icon: "🌡️", label: "Heatwave" },
  FOG: { icon: "🌫️", label: "Fog" },
  DUST_STORM: { icon: "🌪️", label: "Dust Storm" },
  STRONG_WIND: { icon: "💨", label: "Strong Wind" },
  HAILSTORM: { icon: "🌨️", label: "Hailstorm" },
  CYCLONE: { icon: "🌀", label: "Cyclone" },
  OTHER: { icon: "🌐", label: "Weather Event" },
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
  const sizeClass = { sm: "text-base", md: "text-xl", lg: "text-3xl" }[size];

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={sizeClass} role="img" aria-label={label}>
        {icon}
      </span>
      {showLabel && <span className="event-label">{label}</span>}
    </span>
  );
}
