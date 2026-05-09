import { ProjectScanForm } from "@/components/ProjectScanForm";
import { listModelProviders, listProjects } from "@/lib/api";

export default async function ProjectsPage() {
  const [modelProviders, projects] = await Promise.all([listModelProviders(), listProjects()]);
  return <ProjectScanForm modelProviders={modelProviders} projects={projects} />;
}
