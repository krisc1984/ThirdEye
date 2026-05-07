const links = [
  { href: "/projects", label: "Projects" },
  { href: "/playbooks", label: "Playbooks" },
  { href: "/review", label: "Review" },
  { href: "/settings/models", label: "Model Settings" }
];

export default function HomePage() {
  return (
    <main>
      <h1>AI Tech Review</h1>
      <p>Distill local project code and docs into review playbooks.</p>
      <nav>
        <ul>
          {links.map((link) => (
            <li key={link.href}>
              <a href={link.href}>{link.label}</a>
            </li>
          ))}
        </ul>
      </nav>
    </main>
  );
}

