import { GraphCompositeManager } from "@/components/GraphCompositeManager";
import { compileGraphComposite, listGraphCapabilities, listGraphComposites } from "@/lib/api";

export default async function GraphCompositesPage() {
  const [composites, capabilities] = await Promise.all([listGraphComposites(), listGraphCapabilities()]);
  const compileResults = Object.fromEntries(
    await Promise.all(
      composites.map(async (composite) => [composite.id, await compileGraphComposite(composite.id)] as const)
    )
  );

  return <GraphCompositeManager initialComposites={composites} capabilities={capabilities} compileResults={compileResults} />;
}
