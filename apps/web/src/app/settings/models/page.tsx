import { ModelProviderForm } from "@/components/ModelProviderForm";
import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";
import { listModelProviders } from "@/lib/api";

export default async function ModelSettingsPage() {
  const providers = await listModelProviders();

  return (
    <div className="page-stack">
      <SettingsSectionTabs active="models" />
      <ModelProviderForm initialProviders={providers} />
    </div>
  );
}
