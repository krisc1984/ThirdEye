import { ModelProviderForm } from "@/components/ModelProviderForm";
import { listModelProviders } from "@/lib/api";

export default async function SettingsPage() {
  const providers = await listModelProviders();

  return <ModelProviderForm initialProviders={providers} />;
}
