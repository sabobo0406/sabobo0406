"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "ダッシュボード", icon: "📊" },
  { href: "/competitors", label: "競合巡回", icon: "🔭" },
  { href: "/transcribe", label: "文字起こし→記事", icon: "✍️" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-black/10 bg-white/70 backdrop-blur sticky top-0 z-10">
      <nav className="mx-auto max-w-6xl px-4 py-3 flex items-center gap-1 sm:gap-2">
        <Link href="/" className="font-bold text-lg mr-4 shrink-0">
          くるくる<span className="text-accent">.</span>
        </Link>
        <div className="flex gap-1 overflow-x-auto">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap transition-colors ${
                  active ? "bg-ink text-white" : "text-sub hover:bg-black/5"
                }`}
              >
                <span className="mr-1">{l.icon}</span>
                {l.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
