"use client";

import Link from "next/link";

export default function Navbar() {
  return (
    <header className="border-b border-border sticky top-0 z-20 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_24px_theme(colors.cyan.400)]" />
          <Link href="/" className="font-plex font-semibold tracking-tight hover:opacity-80 transition-opacity">
            MUONRY
          </Link>
        </div>
        <nav className="flex items-center gap-3 text-sm">
          <a
            href="https://github.com/justrach/muonry"
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline gap-1 px-3 py-1.5"
          >
            <span>GitHub</span>
            <span aria-hidden>★</span>
          </a>
          <a
            href="https://github.com/justrach/muonry#readme"
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline px-3 py-1.5"
          >
            Docs
          </a>
          <Link href="/about" className="btn btn-outline px-3 py-1.5">
            About
          </Link>
        </nav>
      </div>
    </header>
  );
}

