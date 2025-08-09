import type { Metadata } from "next";
import { Geist, Geist_Mono, JetBrains_Mono, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["100","200","300","400","500","600","700"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    template: "%s - Muonry",
    default: "Muonry - Terminal-first AI coding agent",
  },
  description:
    "A transparent, hackable AI coding agent built in under 1200 lines of code. Open source, free, and privacy-first.",
  keywords: [
    "AI coding agent",
    "open source agent",
    "developer tools",
    "transparent AI",
    "coding assistant",
  ],
  authors: [{ name: "Muonry" }],
  creator: "Muonry",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  icons: {
    // Use classic .ico as the favicon, per request
    icon: "/favicon.ico",
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Muonry - Terminal-first AI coding agent",
    description:
      "A transparent, hackable AI coding agent built in under 1200 lines of code. Open source, free, and privacy-first.",
    type: "website",
    url: siteUrl,
  },
  twitter: {
    card: "summary_large_image",
    title: "Muonry - Terminal-first AI coding agent",
    description:
      "A transparent, hackable AI coding agent built in under 1200 lines of code.",
  },
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${jetBrainsMono.variable} ${ibmPlexMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
