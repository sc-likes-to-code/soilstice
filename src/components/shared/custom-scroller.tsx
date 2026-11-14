"use client";
import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SectionTarget {
  id: string;
  label: string;
  short: string;
}

const SECTIONS: SectionTarget[] = [
  { id: "hero", label: "Overview", short: "01" },
  { id: "the-problem", label: "The Challenge", short: "02" },
  { id: "how-it-works", label: "The Pipeline", short: "03" },
  { id: "capabilities", label: "Capabilities", short: "04" },
  { id: "transparency", label: "Scientific Honesty", short: "05" },
  { id: "datasets", label: "Data Sources", short: "06" },
  { id: "action", label: "Get Started", short: "07" },
];

/**
 * Custom Floating Section Scroller & Scroll Progress
 * Crafted for SOILSTICE's forest green and earthy gold aesthetic.
 */
export function CustomScroller() {
  const [activeId, setActiveId] = useState<string>("hero");
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [showTopButton, setShowTopButton] = useState<boolean>(false);

  useEffect(() => {
    const handleScroll = () => {
      // Calculate total page scroll percentage
      const totalScroll = document.documentElement.scrollTop;
      const windowHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      if (windowHeight > 0) {
        const progress = (totalScroll / windowHeight) * 100;
        setScrollProgress(progress);
      }
      setShowTopButton(totalScroll > 450);

      // Determine which section is currently active in the viewport
      const scrollPosition = window.scrollY + window.innerHeight * 0.35;
      for (let i = SECTIONS.length - 1; i >= 0; i--) {
        const el = document.getElementById(SECTIONS[i].id);
        if (el) {
          const top = el.offsetTop;
          if (scrollPosition >= top) {
            setActiveId(SECTIONS[i].id);
            break;
          }
        }
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <>
      {/* ── Top Reading Progress Bar (Earthy Gold & Forest Glow) ── */}
      <div
        className="pointer-events-none fixed left-0 top-0 z-50 h-[3px] w-full origin-left bg-transparent"
        aria-hidden
      >
        <div
          className="h-full bg-gradient-to-r from-forest-500 via-wheat-400 to-emerald-400 shadow-[0_0_8px_rgba(201,154,62,0.6)] transition-all duration-150"
          style={{ width: `${scrollProgress}%` }}
        />
      </div>

      {/* ── Floating Right-Hand Section Navigation Rail ── */}
      <nav
        aria-label="Section scroller"
        className="fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 flex-col items-center gap-2.5 rounded-full border border-paper/15 bg-forest-950/70 p-2.5 shadow-2xl backdrop-blur-md transition-opacity duration-300 md:flex lg:right-6"
      >
        {SECTIONS.map(({ id, label, short }) => {
          const isActive = activeId === id;
          return (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              aria-label={`Scroll to ${label}`}
              className="group relative flex items-center justify-center py-0.5 focus:outline-none"
            >
              {/* Tooltip on hover */}
              <span className="pointer-events-none absolute right-full mr-3.5 hidden whitespace-nowrap rounded-lg border border-paper/15 bg-forest-950/95 px-2.5 py-1 text-[11px] font-semibold text-paper shadow-xl backdrop-blur group-hover:flex">
                <span className="font-mono text-wheat-300 mr-1.5">{short}</span>
                <span>{label}</span>
              </span>

              {/* Scroller tick/pill */}
              <div
                className={cn(
                  "rounded-full transition-all duration-300",
                  isActive
                    ? "h-6 w-2 bg-wheat-400 shadow-[0_0_10px_rgba(201,154,62,0.8)]"
                    : "h-2 w-2 bg-paper/30 hover:bg-wheat-200/80 hover:scale-125",
                )}
              />
            </button>
          );
        })}

        {/* Back to Top Icon Button */}
        {showTopButton && (
          <button
            onClick={() => scrollTo("hero")}
            aria-label="Back to top"
            className="group relative mt-1.5 grid h-6 w-6 place-items-center rounded-full border border-paper/15 bg-forest-900/80 text-forest-200 transition-all hover:bg-wheat-500 hover:text-forest-950 hover:shadow-md"
            title="Back to top"
          >
            <ArrowUp className="h-3 w-3 transition-transform group-hover:-translate-y-0.5" />
          </button>
        )}
      </nav>
    </>
  );
}
