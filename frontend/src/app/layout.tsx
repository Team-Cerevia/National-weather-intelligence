import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "METEORA | National Weather Big Data Analytics Platform",
  description:
    "METEORA - Real-time weather incident monitoring and evidence-based verification for India. Powered by multi-source ingestion, NLP correlation, and spatial analysis.",
  keywords: [
    "METEORA",
    "weather intelligence",
    "India weather",
    "disaster monitoring",
    "real-time alerts",
    "IMD",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="app-body">{children}</body>
    </html>
  );
}
