import { GraphRunsCockpit } from "@/components/GraphRunsCockpit";
import { listGraphPlaybooks, listGraphRuns } from "@/lib/api";

export default async function GraphRunsPage() {
  const [runs, playbooks] = await Promise.all([listGraphRuns(), listGraphPlaybooks()]);

  return <GraphRunsCockpit initialRuns={runs} playbooks={playbooks} />;
}
