import Link from 'next/link';
import Navbar from '@/components/Navbar';
export const metadata = {
  title: "About",
  description: "Why Muonry was built as a transparent, hackable AI coding agent in under 1200 lines of code.",
};

export default function AboutPage() {
  return (
    <div>
      <Navbar />
      <div className="min-h-screen bg-white dark:bg-gray-900">
        <div className="max-w-4xl mx-auto px-4 py-16">
        <Link 
          href="/" 
          className="inline-flex items-center text-cyan-600 hover:text-cyan-700 dark:text-cyan-400 dark:hover:text-cyan-300 mb-8"
        >
          <svg 
            className="w-4 h-4 mr-2" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M15 19l-7-7 7-7" 
            />
          </svg>
          Back to Home
        </Link>

        <div className="space-y-12">
          <header className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
              Why Muonry Was Built
            </h1>
            <p className="text-xl text-gray-600 dark:text-gray-300">
              A transparent, hackable AI coding agent built in under 1200 lines
            </p>
          </header>

          <div className="bg-gradient-to-r from-cyan-50 to-purple-50 dark:from-cyan-900/20 dark:to-purple-900/20 rounded-2xl p-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              The Problem
            </h2>
            <p className="text-lg text-gray-700 dark:text-gray-300 mb-4">
              Most AI coding tools are black boxes. You send your code to a server, 
              magic happens, and you get results back. But what exactly is happening? 
              What data is being collected? What prompts are being used? How does 
              the agent actually work under the hood?
            </p>
            <p className="text-lg text-gray-700 dark:text-gray-300">
              This opacity creates several problems: privacy concerns, vendor lock-in, 
              inability to customize behavior, and most importantly - you can't learn 
              from or improve the system.
            </p>
          </div>

          <div className="bg-gradient-to-r from-purple-50 to-cyan-50 dark:from-purple-900/20 dark:to-cyan-900/20 rounded-2xl p-8">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              The 1200-Line Challenge
            </h2>
            <p className="text-lg text-gray-700 dark:text-gray-300 mb-4">
              We set out to build a complete AI coding agent that anyone could understand, 
              modify, and extend - all in under 1200 lines of code. Not 1200 lines of 
              business logic plus thousands of dependencies. 1200 lines total.
            </p>
            <p className="text-lg text-gray-700 dark:text-gray-300 mb-6">
              This constraint forces clarity. Every line matters. Every feature is essential. 
              The result is a system you can read in an afternoon, understand completely, 
              and adapt to your needs.
            </p>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <code className="text-sm text-gray-800 dark:text-gray-200">
                $ find . -type f -name "*.py" -not -path "*/\.*" | xargs wc -l | tail -1
                <br />
                1187 total
              </code>
            </div>
          </div>

          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              What We Believe
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Transparency
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Every prompt, every decision, every line of code is visible and auditable.
                </p>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Hackability
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Want to add support for a new language or tool? The code is designed to be modified.
                </p>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Privacy
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  Runs locally. Your code never leaves your machine unless you want it to.
                </p>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  Freedom
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  No vendor lock-in. No API keys required. Modify, distribute, and use however you want.
                </p>
              </div>
            </div>
          </div>

          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              What's Possible in 1200 Lines?
            </h2>
            <p className="text-lg text-gray-700 dark:text-gray-300 mb-6">
              Despite the constraint, Muonry provides a complete AI coding experience:
            </p>
            <div className="grid md:grid-cols-3 gap-4 text-left">
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Core Agent</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Planning, execution, and error handling
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">File Operations</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Read, write, create, and modify files
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Shell Commands</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Run tests, install packages, execute commands
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Web Search</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Research APIs, documentation, and solutions
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Project Analysis</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Understand existing codebases and dependencies
                </p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Interactive CLI</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Natural language interaction and feedback
                </p>
              </div>
            </div>
          </div>

          <div className="text-center pt-8">
            <Link 
              href="https://github.com/your-org/muonry"
              className="inline-flex items-center px-6 py-3 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
            >
              View Source on GitHub
              <svg className="w-4 h-4 ml-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </Link>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}
