import { AgentWorkspace } from "@/components/AgentWorkspace";
import { listModelProviders, listPlaybooks, listProjects, listSkills } from "@/lib/api";

export default async function ReviewPage() {
  const [playbooks, modelProviders, projects, skills] = await Promise.all([
    listPlaybooks(),
    listModelProviders(),
    listProjects(),
    listSkills()
  ]);

  return <AgentWorkspace playbooks={playbooks} modelProviders={modelProviders} projects={projects} skills={skills} />;
}
