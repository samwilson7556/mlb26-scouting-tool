import Link from "next/link";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/games", label: "Games" },
  { href: "/opponents", label: "Opponents" },
  { href: "/scout", label: "Scout" },
  { href: "/sync", label: "Sync" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <header
        className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/95 backdrop-blur"
        style={{
          borderBottom: "1px solid rgba(30, 41, 59, 0.9)",
          background: "rgba(2, 6, 23, 0.96)",
        }}
      >
        <div
          className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4"
          style={{
            maxWidth: "80rem",
            margin: "0 auto",
            padding: "1rem 1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "1.5rem",
          }}
        >
          <Link
            href="/"
            className="group flex items-center gap-3"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              textDecoration: "none",
            }}
          >
            <div
              className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-sm font-black text-white shadow-lg shadow-blue-950/50"
              style={{
                width: "2.25rem",
                height: "2.25rem",
                borderRadius: "0.85rem",
                background: "#2563eb",
                color: "white",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: "0.875rem",
              }}
            >
              26
            </div>

            <div>
              <div
                className="text-base font-bold tracking-tight text-white"
                style={{
                  color: "white",
                  fontSize: "1rem",
                  fontWeight: 800,
                  lineHeight: 1.1,
                }}
              >
                MLB 26 Scout
              </div>
              <div
                className="text-xs text-slate-500"
                style={{
                  color: "#64748b",
                  fontSize: "0.75rem",
                  marginTop: "0.15rem",
                }}
              >
                Game history & scouting
              </div>
            </div>
          </Link>

          <nav
            className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 p-1 shadow-xl shadow-black/20"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.35rem",
              borderRadius: "1rem",
              border: "1px solid rgba(30, 41, 59, 0.95)",
              background: "rgba(15, 23, 42, 0.92)",
              boxShadow: "0 18px 45px rgba(0, 0, 0, 0.25)",
              whiteSpace: "nowrap",
            }}
          >
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-xl px-4 py-2 text-sm font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-white"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  minWidth: "5.25rem",
                  padding: "0.65rem 1rem",
                  borderRadius: "0.8rem",
                  color: "#cbd5e1",
                  fontSize: "0.875rem",
                  fontWeight: 700,
                  textDecoration: "none",
                  lineHeight: 1,
                }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      <div
        className="mx-auto max-w-7xl px-6 py-8"
        style={{
          maxWidth: "80rem",
          margin: "0 auto",
          padding: "2rem 1.5rem",
        }}
      >
        {children}
      </div>
    </main>
  );
}