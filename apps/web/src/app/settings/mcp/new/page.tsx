import { McpServiceCreateForm } from "@/components/McpServiceCreateForm";
import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";

export default async function NewMcpServicePage() {
  return (
    <div className="page-stack">
      <SettingsSectionTabs active="mcp" />
      <McpServiceCreateForm />
    </div>
  );
}
