import { McpSettings } from "@/components/McpSettings";
import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";
import { listMcpServers } from "@/lib/api";

export default async function McpSettingsPage() {
  const services = await listMcpServers();

  return (
    <div className="page-stack">
      <SettingsSectionTabs active="mcp" />
      <McpSettings initialServices={services} />
    </div>
  );
}
