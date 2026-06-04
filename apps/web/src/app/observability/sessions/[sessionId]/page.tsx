import { ObservabilitySessionDetail } from "@/components/ObservabilitySessionDetail";
import {
  getObservabilityEvents,
  getObservabilityMetrics,
  getObservabilitySessionDetail,
  getObservabilityTasks,
  getObservabilityTimeline,
  listObservabilitySessions,
} from "@/lib/api";

type ObservabilitySessionDetailPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function ObservabilitySessionDetailPage({ params }: ObservabilitySessionDetailPageProps) {
  const { sessionId } = await params;
  const [sessions, summary, timeline, tasks, metrics, events] = await Promise.all([
    listObservabilitySessions(),
    getObservabilitySessionDetail(sessionId),
    getObservabilityTimeline(sessionId),
    getObservabilityTasks(sessionId),
    getObservabilityMetrics(sessionId),
    getObservabilityEvents(sessionId),
  ]);

  return (
    <ObservabilitySessionDetail
      sessionId={sessionId}
      sessions={sessions}
      summary={summary}
      timeline={timeline}
      tasks={tasks}
      metrics={metrics}
      events={events}
    />
  );
}
