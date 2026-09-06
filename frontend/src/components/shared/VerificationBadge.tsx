import type { VerificationStatus } from "@/lib/types";

const config: Record<VerificationStatus, { label: string; className: string }> =
  {
    SUPPORTED: { label: "Supported", className: "badge-verify-supported" },
    VERIFIED: { label: "Verified", className: "badge-verify-verified" },
    UNVERIFIED: { label: "Unverified", className: "badge-verify-unverified" },
    CONTRADICTED: {
      label: "Contradicted",
      className: "badge-verify-contradicted",
    },
    PENDING_REVIEW: {
      label: "Pending Review",
      className: "badge-verify-pending",
    },
  };

export function VerificationBadge({
  status,
}: {
  status: VerificationStatus;
}) {
  const { label, className } = config[status] ?? config.UNVERIFIED;
  return <span className={`badge ${className}`}>{label}</span>;
}
