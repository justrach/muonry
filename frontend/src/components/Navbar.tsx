"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navItems = [
    { href: "/", label: "Home" },
    { href: "/about", label: "About" },
    { href: "https://github.com/justrach/muonry#readme", label: "Docs", external: true },
    { href: "https://github.com/justrach/muonry", label: "GitHub", external: true },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header
      className={`
        fixed top-0 left-0 right-0 z-50 transition-all duration-300
        ${isScrolled
          ? "bg-background/80 backdrop-blur-md border-b border-border/50 shadow-sm"
          : "bg-transparent"
        }
      `}
    >
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 group transition-transform hover:scale-105 hover:rotate-1"
            aria-label="Muonry Home"
          >
            <div className="relative">
              <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.8)] group-hover:shadow-[0_0_24px_rgba(6,182,212,1)] transition-all duration-300" />
              <div className="absolute inset-0 animate-ping rounded-full bg-cyan-400/30 opacity-75 group-hover:opacity-100 transition-opacity" />
            </div>
            <span className="font-plex font-bold text-lg tracking-tight text-gradient-cm group-hover:opacity-80 transition-all duration-300">
              MUONRY
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const active = isActive(item.href);
              const hovered = hoveredItem === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  target={item.external ? "_blank" : undefined}
                  rel={item.external ? "noreferrer" : undefined}
                  className={`
                    relative px-4 py-2 text-sm font-medium rounded-md transition-all duration-300
                    ${active
                      ? "text-cyan-400 dark:text-cyan-300"
                      : "text-foreground/70 hover:text-foreground"
                    }
                  `}
                  onMouseEnter={() => setHoveredItem(item.href)}
                  onMouseLeave={() => setHoveredItem(null)}
                  aria-current={active ? "page" : undefined}
                >
                  {/* Background highlight */}
                  <div className={`
                    absolute inset-0 bg-cyan-500/5 dark:bg-cyan-400/10 rounded-md
                    transition-all duration-300 scale-95 opacity-0
                    ${hovered ? "opacity-100 scale-100" : ""}
                  `} />
                  
                  {/* Active/hover indicator */}
                  <div className={`
                    absolute bottom-0 left-1/2 -translate-x-1/2 h-0.5
                    transition-all duration-300
                    ${active
                      ? "w-3/4 bg-cyan-400 dark:bg-cyan-300"
                      : hovered
                      ? "w-1/2 bg-cyan-400/60 dark:bg-cyan-300/60"
                      : "w-0"
                    }
                  `} />
                  
                  <span className="relative z-10">{item.label}</span>
                  {item.external && (
                    <span className="ml-1 opacity-50" aria-hidden>↗</span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-md text-foreground/70 hover:text-foreground hover:bg-muted/50 transition-colors"
            aria-label="Toggle mobile menu"
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-menu"
          >
            {isMobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div
          id="mobile-menu"
          className="md:hidden border-t border-border/50 bg-background/95 backdrop-blur-md"
        >
          <nav className="px-4 py-4 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noreferrer" : undefined}
                className={`
                  block px-3 py-2 text-base font-medium rounded-md transition-all duration-200
                  ${isActive(item.href)
                    ? "bg-cyan-500/10 text-cyan-400 dark:text-cyan-300 border-l-2 border-cyan-400"
                    : "text-foreground/70 hover:text-foreground hover:bg-cyan-500/5 dark:hover:bg-cyan-400/10 border-l-2 border-transparent hover:border-cyan-400/30"
                  }
                `}
                onClick={() => setIsMobileMenuOpen(false)}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
                {item.external && (
                  <span className="ml-1 opacity-50" aria-hidden>↗</span>
                )}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}