import { notFound } from "next/navigation";

import { PlaybookDetail } from "@/components/PlaybookDetail";
import { getPlaybook } from "@/lib/api";

type PlaybookDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function PlaybookDetailPage({ params }: PlaybookDetailPageProps) {
  const { id } = await params;

  try {
    const playbook = await getPlaybook(id);
    return <PlaybookDetail playbook={playbook} />;
  } catch {
    notFound();
  }
}
