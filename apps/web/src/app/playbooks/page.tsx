import { PlaybookList } from "@/components/PlaybookList";
import { listPlaybooks, listProjects } from "@/lib/api";

export default async function PlaybooksPage() {
  const [playbooks, projects] = await Promise.all([listPlaybooks(), listProjects()]);

  return <PlaybookList playbooks={playbooks} projects={projects} />;
}
