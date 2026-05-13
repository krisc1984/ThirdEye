import { BusinessAgentSettings } from "@/components/BusinessAgentSettings";
import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";
import { listBusinessAgents } from "@/lib/api";

export default async function AgentSettingsPage() {
  const agents = await listBusinessAgents();

  return (
    <div className="page-stack">
      <SettingsSectionTabs active="agents" />
      <BusinessAgentSettings initialAgents={agents} />
    </div>
  );
}

