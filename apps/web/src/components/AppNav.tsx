import Link from "next/link";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/projects", label: "Projects" },
  { href: "/playbooks", label: "Playbooks" },
  { href: "/review", label: "Review" }
];

export function AppNav() {
  return (
    <>
      <nav className="app-nav" aria-label="Primary">
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} className="app-nav__link">
            {item.label}
          </Link>
        ))}
      </nav>
      <Link href="/settings" className="settings-fab" aria-label="打开设置">
        <span className="settings-fab__icon">⚙</span>
        <span className="settings-fab__label">设置</span>
      </Link>
    </>
  );
}
