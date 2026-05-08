import type { Metadata } from "next";
import Link from "next/link";
import { Circuitry, Command, Fingerprint, Gauge } from "@phosphor-icons/react/dist/ssr";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentGate Control Plane",
  description: "Containment-first security gateway and enterprise console for AI agent tool calls.",
  openGraph: {
    title: "AgentGate Control Plane",
    description: "Stop, approve, replay, and evidence every AI tool call.",
    type: "website",
  },
};

const navItems = [
  { href: "/", label: "Front door", icon: Fingerprint },
  { href: "/console", label: "Command center", icon: Gauge },
  { href: "/policies", label: "Policy studio", icon: Circuitry },
  { href: "/operations", label: "Operations", icon: Command },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-dvh overflow-x-hidden">
            <header className="sticky top-0 z-40 border-b border-graphite-900/10 bg-bone-50/82 backdrop-blur-xl">
              <nav className="mx-auto flex max-w-[1500px] items-center justify-between gap-5 px-4 py-3 sm:px-6 lg:px-8" aria-label="Primary">
                <Link href="/" className="group inline-flex items-center gap-3 rounded-full pr-3 text-sm font-semibold text-graphite-950">
                  <span className="grid h-9 w-9 place-items-center rounded-full bg-graphite-950 text-bone-50 transition-transform duration-500 ease-cockpit group-hover:scale-[1.04]">
                    <Fingerprint size={18} weight="duotone" />
                  </span>
                  AgentGate
                </Link>
                <div className="hidden items-center gap-1 rounded-full border border-graphite-900/10 bg-bone-50/80 p-1 shadow-[0_12px_30px_-26px_oklch(0.18_0.012_180_/_0.4)] md:flex">
                  {navItems.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link key={item.href} href={item.href} className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-graphite-650 transition duration-300 ease-cockpit hover:bg-graphite-900 hover:text-bone-50">
                        <Icon size={15} />
                        {item.label}
                      </Link>
                    );
                  })}
                </div>
                <Link href="/reference" className="hidden rounded-full border border-graphite-900/10 bg-bone-50 px-4 py-2 text-sm font-semibold text-graphite-800 transition duration-300 ease-cockpit hover:-translate-y-0.5 hover:border-verdigris-500/40 hover:text-verdigris-900 sm:inline-flex">
                  Reference
                </Link>
              </nav>
            </header>
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
