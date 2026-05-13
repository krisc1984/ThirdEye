import { AgentWorkspace } from "@/components/AgentWorkspace";
import { listBusinessAgents, listModelProviders, listPlaybooks, listProjects, listSkills } from "@/lib/api";

export default async function ReviewPage() {
  const [playbooks, modelProviders, projects, skills, businessAgents] = await Promise.all([
    listPlaybooks(),
    listModelProviders(),
    listProjects(),
    listSkills(),
    listBusinessAgents()
  ]);

  const activeAgent = businessAgents.find((agent) => agent.is_default || agent.status === "active") ?? businessAgents[0] ?? null;

  return (
    <AgentWorkspace
      playbooks={playbooks}
      modelProviders={modelProviders}
      projects={projects}
      skills={skills}
      activeAgentName={activeAgent?.name ?? null}
    />
  );
}
