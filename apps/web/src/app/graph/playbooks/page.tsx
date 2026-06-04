import { GraphPlaybookManager } from "@/components/GraphPlaybookManager";
import { compileGraphPlaybook, listGraphCapabilities, listGraphComposites, listGraphPlaybooks } from "@/lib/api";

export default async function GraphPlaybooksPage() {
  const [playbooks, capabilities, composites] = await Promise.all([
    listGraphPlaybooks(),
    listGraphCapabilities(),
    listGraphComposites(),
  ]);
  const compileResults = Object.fromEntries(
    await Promise.all(
      playbooks.map(async (playbook) => [playbook.id, await compileGraphPlaybook(playbook.id)] as const)
    )
  );

  return (
    <GraphPlaybookManager
      initialPlaybooks={playbooks}
      capabilities={capabilities}
      composites={composites}
      compileResults={compileResults}
    />
  );
}
