import Link from "next/link";

type SettingsSectionTabsProps = {
  active: "agents" | "models" | "skills";
};

const tabs = [
  { id: "agents", href: "/settings/agents", label: "智能体中心" },
  { id: "skills", href: "/settings/skills", label: "技能管理" },
  { id: "models", href: "/settings/models", label: "模型设置" }
] as const;

export function SettingsSectionTabs({ active }: SettingsSectionTabsProps) {
  return (
    <nav className="settings-section-tabs" aria-label="设置分区">
      {tabs.map((tab) => (
        <Link
          key={tab.id}
          href={tab.href}
          className={`settings-section-tabs__item ${active === tab.id ? "settings-section-tabs__item--active" : ""}`}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}
