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
    default: "Muonry - Open Source AI Coding Assistant | LLMCompiler Enhanced",
  },
  description:
    "Muonry is a transparent, fast, and fully controllable AI coding assistant. Built in <1200 lines with LLMCompiler-enhanced parallel tool calling. Open source and extensible.",
  keywords: [
    "AI coding assistant",
    "open source",
    "LLMCompiler",
    "parallel tool calling",
    "developer tools",
    "code generation",
    "automation",
    "terminal-first",
    "transparent AI",
    "coding agent",
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
    icon: "/favicon.ico",
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Muonry - Open Source AI Coding Assistant",
    description:
      "Transparent, fast AI coding assistant with LLMCompiler-enhanced parallel tool calling. Built in <1200 lines.",
    type: "website",
    url: siteUrl,
    images: [
      {
        url: "https://images.muonry.com/og-image.png",
        width: 1200,
        height: 630,
        alt: "Muonry - Open Source AI Coding Assistant",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Muonry - Open Source AI Coding Assistant",
    description:
      "Transparent, fast AI coding assistant with LLMCompiler-enhanced parallel tool calling. Built in <1200 lines.",
    images: ["https://images.muonry.com/og-image.png"],
  },
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
  other: {
    "google-site-verification": "your-google-verification-code", // Add your actual verification code
  },
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
