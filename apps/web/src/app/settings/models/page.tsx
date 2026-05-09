import { ModelProviderForm } from "@/components/ModelProviderForm";
import { listModelProviders } from "@/lib/api";

export default async function ModelSettingsPage() {
  const providers = await listModelProviders();

  return <ModelProviderForm initialProviders={providers} />;
}
