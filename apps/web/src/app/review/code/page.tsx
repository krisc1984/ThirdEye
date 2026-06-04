import { CodeReviewWorkspace } from "@/components/CodeReviewWorkspace";
import { listBusinessAgents, listModelProviders, listPlaybooks, listProjects } from "@/lib/api";

export default async function CodeReviewPage() {
  const [playbooks, modelProviders, projects, businessAgents] = await Promise.all([
    listPlaybooks(),
    listModelProviders(),
    listProjects(),
    listBusinessAgents()
  ]);

  const codeReviewAgent =
    businessAgents.find((agent) => agent.id === "code-review-agent") ??
    businessAgents.find((agent) => agent.name.includes("代码评审")) ??
    null;

  return (
    <CodeReviewWorkspace
      playbooks={playbooks}
      modelProviders={modelProviders}
      projects={projects}
      codeReviewAgent={codeReviewAgent}
    />
  );
}
