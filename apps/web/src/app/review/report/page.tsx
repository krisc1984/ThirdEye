import { ReviewReportWorkspace } from "@/components/ReviewReportWorkspace";
import {
  getKnowledgeWorkspaceBinding,
  getPlaybookById,
  getReviewSession,
  listBusinessAgents,
  listKnowledgeWorkspaceFiles
} from "@/lib/api";

function buildInitialMarkdown(session: Awaited<ReturnType<typeof getReviewSession>>, playbook: Awaited<ReturnType<typeof getPlaybookById>>) {
  const review = session.last_review;
  const keyMessages = session.messages
    .filter((message) => message.role === "assistant" || message.role === "user")
    .slice(-6);

  const keyRisks = review?.key_risks?.length ? review.key_risks : [session.latest_summary ?? "待补充最新评审总结"];
  const suggestedChanges = review?.suggested_changes?.length
    ? review.suggested_changes
    : review?.required_validation?.length
      ? review.required_validation
      : ["补充验证路径，并将关键风险与责任人对应。"];

  const evidenceLines = playbook.evidence.slice(0, 6).map((item) => `- ${item.path}: ${item.summary}`);
  const conversationLines = keyMessages.map(
    (message) => `- ${message.role === "assistant" ? "Agent" : "用户"}（${new Date(message.created_at).toLocaleString("zh-CN")}）：${message.content.replace(/\s+/g, " ").slice(0, 180)}`
  );

  return [
    `# 评审报告`,
    "",
    `## 一、基本信息`,
    `- 会话 ID：${session.id}`,
    `- Playbook：${playbook.metadata.name}`,
    `- 当前结论：${review?.overall_judgement ?? "待确认"}`,
    `- 更新时间：${new Date(session.updated_at).toLocaleString("zh-CN")}`,
    "",
    `## 二、方案概述`,
    session.latest_summary ?? review?.overall_judgement ?? "待补充方案概述。",
    "",
    `## 三、关键风险`,
    ...keyRisks.map((item) => `- ${item}`),
    "",
    `## 四、建议行动`,
    ...suggestedChanges.map((item, index) => `${index + 1}. ${item}`),
    "",
    `## 五、证据引用`,
    ...(evidenceLines.length ? evidenceLines : ["- 暂无结构化证据引用。"]),
    "",
    `## 六、关键会话摘录`,
    ...(conversationLines.length ? conversationLines : ["- 暂无关键会话摘录。"]),
    "",
    `## 七、待确认事项`,
    `- [ ] 是否确认当前评审结论`,
    `- [ ] 是否补充验证结果和责任人`,
    `- [ ] 是否沉淀为正式评审纪要`,
  ].join("\n");
}

export default async function ReviewReportPage({
  searchParams
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const sessionId = typeof params.session_id === "string" ? params.session_id : "";
  const playbookId = typeof params.playbook_id === "string" ? params.playbook_id : "";

  if (!sessionId || !playbookId) {
    throw new Error("missing session_id or playbook_id");
  }

  const [session, playbook, businessAgents] = await Promise.all([
    getReviewSession(sessionId),
    getPlaybookById(playbookId),
    listBusinessAgents()
  ]);

  const projectId = session.project_id ?? playbook.metadata.project_id;
  const [knowledgeBinding, knowledgeListing] = projectId
    ? await Promise.all([
        getKnowledgeWorkspaceBinding(projectId),
        listKnowledgeWorkspaceFiles({ project_id: projectId })
      ])
    : [null, null];

  const activeAgent = businessAgents.find((agent) => agent.is_default || agent.status === "active") ?? businessAgents[0] ?? null;
  const initialMarkdown = buildInitialMarkdown(session, playbook);

  return (
    <ReviewReportWorkspace
      session={session}
      playbook={playbook}
      activeAgentName={activeAgent?.name ?? null}
      initialMarkdown={initialMarkdown}
      knowledgeBinding={knowledgeBinding}
      knowledgeListing={knowledgeListing}
      projectId={projectId}
    />
  );
}
