import { ModelProviderForm } from "@/components/ModelProviderForm";
import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";
import { getTavilySettings, listModelProviders } from "@/lib/api";

export default async function ModelSettingsPage() {
  const [providers, tavilySettings] = await Promise.all([listModelProviders(), getTavilySettings()]);

  return (
    <div className="page-stack">
      <SettingsSectionTabs active="models" />
      <ModelProviderForm initialProviders={providers} initialTavilySettings={tavilySettings} />
    </div>
  );
}
