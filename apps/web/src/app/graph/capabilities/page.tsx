import { GraphCapabilityManager } from "@/components/GraphCapabilityManager";
import { listGraphCapabilities, listGraphCapabilitySources, listModelProviders } from "@/lib/api";

export default async function GraphCapabilitiesPage() {
  const [capabilities, providers, sources] = await Promise.all([
    listGraphCapabilities(),
    listModelProviders(),
    listGraphCapabilitySources(),
  ]);

  return <GraphCapabilityManager initialCapabilities={capabilities} providers={providers} sources={sources} />;
}
