import React from "react";

// Event category → Category color, SVG icon & readable label
interface EventMeta {
  label: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  iconSvg: React.ReactNode;
}

const EVENT_MAP: Record<string, EventMeta> = {
  RAIN: {
    label: "Rain",
    badgeBg: "bg-sky-500/15",
    badgeText: "text-sky-700 dark:text-sky-300",
    badgeBorder: "border-sky-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 14.8A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.2" />
        <path d="M16 14v6" />
        <path d="M8 14v6" />
        <path d="M12 16v6" />
      </svg>
    ),
  },
  FLOOD: {
    label: "Flood",
    badgeBg: "bg-blue-500/15",
    badgeText: "text-blue-700 dark:text-blue-300",
    badgeBorder: "border-blue-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 6c.6 0 1.2.2 1.6.6l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.8-.8 2-.8 2.8 0l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.4-.4 1-.6 1.6-.6" />
        <path d="M2 12c.6 0 1.2.2 1.6.6l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.8-.8 2-.8 2.8 0l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.4-.4 1-.6 1.6-.6" />
        <path d="M2 18c.6 0 1.2.2 1.6.6l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.8-.8 2-.8 2.8 0l1.8 1.8c.8.8 2 .8 2.8 0l1.8-1.8c.4-.4 1-.6 1.6-.6" />
      </svg>
    ),
  },
  WATERLOGGING: {
    label: "Waterlogging",
    badgeBg: "bg-cyan-500/15",
    badgeText: "text-cyan-700 dark:text-cyan-300",
    badgeBorder: "border-cyan-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />
      </svg>
    ),
  },
  THUNDERSTORM: {
    label: "Thunderstorm",
    badgeBg: "bg-indigo-500/15",
    badgeText: "text-indigo-700 dark:text-indigo-300",
    badgeBorder: "border-indigo-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9" />
        <polyline points="13 11 9 17 15 17 11 23" />
      </svg>
    ),
  },
  LIGHTNING: {
    label: "Lightning",
    badgeBg: "bg-amber-500/15",
    badgeText: "text-amber-700 dark:text-amber-300",
    badgeBorder: "border-amber-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
  },
  HEATWAVE: {
    label: "Heatwave",
    badgeBg: "bg-orange-500/15",
    badgeText: "text-orange-700 dark:text-orange-300",
    badgeBorder: "border-orange-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
    ),
  },
  FOG: {
    label: "Fog",
    badgeBg: "bg-slate-500/15",
    badgeText: "text-slate-700 dark:text-slate-300",
    badgeBorder: "border-slate-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="3" y1="10" x2="21" y2="10" />
        <line x1="5" y1="14" x2="19" y2="14" />
        <line x1="7" y1="18" x2="17" y2="18" />
      </svg>
    ),
  },
  DUST_STORM: {
    label: "Dust Storm",
    badgeBg: "bg-stone-500/15",
    badgeText: "text-stone-700 dark:text-stone-300",
    badgeBorder: "border-stone-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
        <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
        <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
      </svg>
    ),
  },
  STRONG_WIND: {
    label: "Strong Wind",
    badgeBg: "bg-teal-500/15",
    badgeText: "text-teal-700 dark:text-teal-300",
    badgeBorder: "border-teal-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
        <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
      </svg>
    ),
  },
  HAILSTORM: {
    label: "Hailstorm",
    badgeBg: "bg-purple-500/15",
    badgeText: "text-purple-700 dark:text-purple-300",
    badgeBorder: "border-purple-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 14.8A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.2" />
        <circle cx="8" cy="18" r="1" fill="currentColor" />
        <circle cx="12" cy="19" r="1" fill="currentColor" />
        <circle cx="16" cy="18" r="1" fill="currentColor" />
      </svg>
    ),
  },
  CYCLONE: {
    label: "Cyclone",
    badgeBg: "bg-rose-500/15",
    badgeText: "text-rose-700 dark:text-rose-300",
    badgeBorder: "border-rose-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: '8s' }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a10 10 0 1 0 10 10" />
        <path d="M12 6a6 6 0 1 0 6 6" />
      </svg>
    ),
  },
  OTHER: {
    label: "Weather Event",
    badgeBg: "bg-gray-500/15",
    badgeText: "text-gray-700 dark:text-gray-300",
    badgeBorder: "border-gray-400/30",
    iconSvg: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
  },
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
  const meta = EVENT_MAP[category?.toUpperCase()] ?? EVENT_MAP.OTHER;
  
  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5 font-semibold",
    lg: "px-3 py-1.5 text-sm gap-2 font-semibold",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border transition-colors shadow-xs ${meta.badgeBg} ${meta.badgeText} ${meta.badgeBorder} ${sizeClasses}`}
      title={meta.label}
    >
      <span className="shrink-0">{meta.iconSvg}</span>
      <span>{meta.label}</span>
    </span>
  );
}

