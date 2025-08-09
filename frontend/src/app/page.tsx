export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top Nav */}
      <header className="border-b border-border sticky top-0 z-20 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-[0_0_24px_theme(colors.cyan.400)]" />
            <a href="/" className="font-plex font-semibold tracking-tight hover:opacity-80 transition-opacity">
              MUONRY
            </a>
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
            <a href="/about" className="btn btn-outline px-3 py-1.5">
              About
            </a>

          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="mx-auto max-w-6xl px-6 py-12 md:py-20">
        <section className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          {/* Copy */}
          <div>
            <h1 className="mt-4 text-4xl md:text-5xl font-plex font-semibold leading-tight">
              The Open Source <span className="text-gradient-cm">Coding Agent</span>
            </h1>
            <p className="mt-4 text-sm md:text-base text-muted-foreground font-jetbrains">
              Bring AI into your dev workflow — transparent, fast, and fully in your control.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <a
                href="https://github.com/justrach/muonry"
                target="_blank"
                rel="noreferrer"
                className="btn btn-gradient"
              >
                Get Started
              </a>
              <a
                href="#video"
                className="btn btn-outline"
              >
                ▶ Watch Video
              </a>
            </div>
          </div>

          {/* Video */}
          <div id="video" className="relative">
            <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-border">
              <video
                src="https://images.muonry.com/muon2.mp4"
                className="h-full w-full object-cover"
                autoPlay
                muted
                loop
                playsInline
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-background/80 to-transparent" />
            </div>
            <p className="mt-3 text-center text-xs text-muted-foreground font-jetbrains">
              Demo: Muonry in action.
            </p>
          </div>
        </section>

      {/* About Section */}
      <section className="mt-20 border-t border-border/60 pt-16">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-plex font-semibold">
            Built in &lt;1200 Lines
          </h2>
          <p className="mt-4 text-base text-muted-foreground font-jetbrains">
            Why we created Muonry — a transparent, hackable coding agent
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
          <div className="rounded-lg border border-border p-6">
            <h3 className="text-lg font-semibold font-plex mb-3">The Problem</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Existing AI coding tools are black boxes. You can't see what they're doing, can't modify their behavior, and can't run them locally. They're expensive, opaque, and locked behind APIs.
            </p>
          </div>

          <div className="rounded-lg border border-border p-6">
            <h3 className="text-lg font-semibold font-plex mb-3">Our Solution</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Muonry is an open, free agent that anyone can understand, modify, and build upon. We've kept the entire codebase under 1200 lines of code — small enough to read in one sitting, powerful enough to be genuinely useful.
            </p>
          </div>
        </div>
      </section>

        {/* Key Features */}
        <section className="mt-16 border-t border-border/60 pt-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-lg border border-border p-5">
              <div className="text-2xl">⚡</div>
              <h3 className="mt-2 font-semibold font-plex">Fast & Lightweight</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Built for low latency and minimal resources — written in Rust, with a tiny surface area you can reason about.
              </p>
            </div>
            <div className="rounded-lg border border-border p-5">
              <div className="text-2xl">🔍</div>
              <h3 className="mt-2 font-semibold font-plex">Fully Transparent</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                100% open source. No hidden APIs.
              </p>
            </div>
            <div className="rounded-lg border border-border p-5">
              <div className="text-2xl">🔗</div>
              <h3 className="mt-2 font-semibold font-plex">Extensible</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Bring your own provider under the hood — Groq, Cerebras, OpenRouter, and more. Works with Python, JS, and beyond.
              </p>
            </div>
          </div>
        </section>

        {/* Interactive Demo */}
        <section className="mt-16" id="demo">
          <h2 className="text-xl font-semibold">Interactive Demo</h2>
          <p className="text-sm text-muted-foreground mt-1 font-jetbrains">
            Try refactoring code on the left; Muonry explains and improves on the right.
          </p>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left: Simple text description of tool flow */}
            <div className="rounded-lg border border-border p-4">
              <div className="text-xs text-muted-foreground mb-2 font-jetbrains">How It Works</div>
              <div className="prose prose-invert max-w-none text-sm leading-relaxed">
                <p>
                  You ask for a change (e.g., “Refactor function X”). Muonry plans the task and applies it to your repo using safe, auditable tool calls:
                </p>
                <ul className="list-disc pl-5 space-y-1">
                  <li><code>read_file</code> / <code>grep</code>: find code and gather context.</li>
                  <li><code>apply_patch</code>: make precise edits via small diffs.</li>
                  <li><code>run_shell</code> / <code>smart_run_shell</code>: run builds/tests; suggest or apply safe fixes.</li>
                  <li><code>update_plan</code>: keep a short, evolving TODO of steps.</li>
                  <li><code>interactive_shell</code>: only for short CLI wizards (e.g., scaffolding).</li>
                </ul>
                <p>
                  Everything happens locally in your workspace. You can use any LLM provider by setting API keys (Groq, Cerebras, OpenRouter, etc.). Secrets aren’t printed, and destructive actions are avoided unless you ask for them.
                </p>
              </div>
            </div>

            {/* Right: Keep response panel for now */}
            <div className="rounded-lg border border-border p-4 min-h-56">
              <div className="text-xs text-muted-foreground mb-2 font-jetbrains">Muonry Response</div>
              <div className="h-40 rounded bg-muted/50 border border-dashed border-border p-4 text-muted-foreground text-sm font-jetbrains leading-relaxed">
                Muonry explains what it’s doing, shows patches it applies, and summarizes build/test output. You can stop at any time or ask it to continue.
              </div>
            </div>
          </div>
        </section>

        {/* Architecture Overview */}
        <section className="mt-16">
          <h2 className="text-xl font-semibold">Architecture Overview</h2>
          <p className="text-sm text-muted-foreground mt-1 font-jetbrains">
            Terminal/CLI → Muonry Core → Tools → Providers → Project Files
          </p>
          <div className="mt-6 rounded-lg border border-border p-6">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Badge>Terminal/CLI</Badge>
              <Arrow />
              <Badge>Muonry Core</Badge>
              <Arrow />
              <Badge>Tools</Badge>
              <Arrow />
              <Badge>Providers</Badge>
              <Arrow />
              <Badge>Project Files</Badge>
            </div>
            <div className="mt-3 text-xs text-muted-foreground font-jetbrains">
              Tools: file ops, shell, patching, planner, websearch • Providers: Groq, Cerebras, Exa (optional)
            </div>
          </div>
        </section>

        {/* Community */}
        <section className="mt-16">
          <h2 className="text-xl font-semibold">Community</h2>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="rounded-lg border border-border p-5">
              <div className="text-sm text-muted-foreground">Contributors</div>
              <div className="mt-3 flex -space-x-2 items-center">
                {/* Lead contributor */}
                <a
                  href="https://github.com/justrach"
                  target="_blank"
                  rel="noreferrer"
                  title="justrach"
                  className="block h-8 w-8 overflow-hidden rounded-full border border-border ring-1 ring-border/60"
                >
                  <img
                    src="https://github.com/justrach.png?size=64"
                    alt="justrach"
                    className="h-full w-full object-cover"
                  />
                </a>
                {/* Placeholder contributors */}
                {Array.from({ length: 4 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-8 w-8 rounded-full bg-muted border border-border grid place-items-center text-[10px] text-muted-foreground/80"
                    title="(this could be you)"
                  >
                    +
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-border p-5">
              <div className="text-sm text-muted-foreground">GitHub</div>
              <a
                href="https://github.com/justrach/muonry"
                target="_blank"
                rel="noreferrer"
                className="mt-3 btn btn-outline gap-2"
              >
                Star the repo
                <span aria-hidden>★</span>
              </a>
            </div>
            <div className="rounded-lg border border-border p-5">
              <div className="text-sm text-muted-foreground">Chat</div>
              <div className="mt-3 text-sm text-muted-foreground">Discord / Matrix (coming soon)</div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="mt-16 mb-20 rounded-xl border border-border p-8 text-center">
          <p className="text-lg md:text-xl font-medium">
            Muonry is open to everyone — start coding with your AI partner today.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <a
              href="https://github.com/justrach/muonry"
              target="_blank"
              rel="noreferrer"
              className="btn btn-gradient"
            >
              Install Now
            </a>
            <a
              href="https://github.com/justrach/muonry"
              target="_blank"
              rel="noreferrer"
              className="btn btn-outline"
            >
              Star on GitHub
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md border border-border bg-secondary text-secondary-foreground px-3 py-1 text-xs">
      {children}
    </span>
  );
}

function Arrow() {
  return <span aria-hidden className="text-muted-foreground">→</span>;
}
