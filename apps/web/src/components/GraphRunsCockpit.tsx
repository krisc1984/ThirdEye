"use client";

import { useMemo, useState, useTransition } from "react";

import type { GraphPlaybookDefinition, GraphRun } from "@/lib/api";
import { createGraphRun, getGraphRun, listGraphRuns } from "@/lib/api";

import { GraphRunCanvas } from "@/components/GraphRunCanvas";
import { GraphRunDetail } from "@/components/GraphRunDetail";
import { GraphRunList } from "@/components/GraphRunList";

type GraphRunsCockpitProps = {
  initialRuns: GraphRun[];
  playbooks: GraphPlaybookDefinition[];
};

export function GraphRunsCockpit({ initialRuns, playbooks }: GraphRunsCockpitProps) {
  const [runs, setRuns] = useState(initialRuns);
  const [selectedRun, setSelectedRun] = useState<GraphRun | null>(initialRuns[0] ?? null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(initialRuns[0]?.current_node_id ?? null);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState(sampleInitialPlaybookId(playbooks));
  const [inputPayloadText, setInputPayloadText] = useState('{\n  "competitor": "Acme",\n  "topic": "weekly-brief"\n}');
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const selectedPlaybook = useMemo(
    () => playbooks.find((playbook) => playbook.id === selectedPlaybookId) ?? null,
    [playbooks, selectedPlaybookId]
  );

  const canvasPlaybook = useMemo(
    () => playbooks.find((playbook) => playbook.id === selectedRun?.graph_playbook_id) ?? null,
    [playbooks, selectedRun?.graph_playbook_id]
  );

  const samplePlaybook =
    playbooks.find((playbook) => playbook.id === "graph_weekly_competitor_report") ?? playbooks[0] ?? null;

  function handleRefresh() {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const nextRuns = await listGraphRuns();
        setRuns(nextRuns);
        if (selectedRun) {
          const refreshed = nextRuns.find((run) => run.id === selectedRun.id);
          if (refreshed) {
            setSelectedRun(await getGraphRun(refreshed.id));
          }
        } else {
          setSelectedRun(nextRuns[0] ?? null);
        }
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "刷新运行列表失败。");
      }
    });
  }

  function handleStartSampleRun() {
    if (!samplePlaybook) {
      return;
    }
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const nextRun = await createGraphRun(samplePlaybook.id, {
          input_payload: { competitor: "Acme", topic: "weekly-brief" }
        });
        setRuns((current) => [nextRun, ...current.filter((run) => run.id !== nextRun.id)]);
        setSelectedRun(nextRun);
        setSelectedNodeId(nextRun.current_node_id ?? null);
        setSelectedPlaybookId(samplePlaybook.id);
        setInputPayloadText(JSON.stringify(nextRun.input_payload, null, 2));
        setStatusMessage(`已启动样例运行：${samplePlaybook.name}`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "启动 sample run 失败。");
      }
    });
  }

  function handlePlaybookChange(value: string) {
    setSelectedPlaybookId(value);
    if (value === "graph_weekly_competitor_report") {
      setInputPayloadText('{\n  "competitor": "Acme",\n  "topic": "weekly-brief"\n}');
      return;
    }
    setInputPayloadText("{}");
  }

  function handleLaunchRun() {
    if (!selectedPlaybook) {
      setError("请先选择一个剧本。");
      return;
    }
    setError(null);
    setStatusMessage(null);
    let inputPayload: Record<string, unknown>;
    try {
      const parsed = JSON.parse(inputPayloadText || "{}");
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("运行输入必须是 JSON 对象。");
      }
      inputPayload = parsed as Record<string, unknown>;
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "运行输入不是合法 JSON。");
      return;
    }

    startTransition(async () => {
      try {
        const nextRun = await createGraphRun(selectedPlaybook.id, {
          input_payload: inputPayload,
        });
        setRuns((current) => [nextRun, ...current.filter((run) => run.id !== nextRun.id)]);
        setSelectedRun(nextRun);
        setSelectedNodeId(nextRun.current_node_id ?? null);
        setStatusMessage(`已启动运行：${selectedPlaybook.name}`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "启动运行失败。");
      }
    });
  }

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <section className="workspace-brand">
          <div className="workspace-brand__mark">▶</div>
          <div>
            <strong>运行台</strong>
            <span>任务驾驶舱</span>
          </div>
        </section>

        <section className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <strong>运行层启动表单</strong>
          </div>
          <label className="settings-field" style={{ gap: 8 }}>
            <span>选择剧本</span>
            <select value={selectedPlaybookId} onChange={(event) => handlePlaybookChange(event.target.value)}>
              <option value="">请选择剧本</option>
              {playbooks.map((playbook) => (
                <option key={playbook.id} value={playbook.id}>
                  {playbook.name} · {playbook.id}
                </option>
              ))}
            </select>
          </label>
          <label className="settings-field" style={{ gap: 8 }}>
            <span>输入载荷 JSON</span>
            <textarea
              value={inputPayloadText}
              onChange={(event) => setInputPayloadText(event.target.value)}
              placeholder='{\n  "topic": "weekly-brief"\n}'
              style={{ minHeight: 160, fontFamily: "Consolas, Monaco, monospace" }}
            />
          </label>
          <button
            type="button"
            className="workspace-primary-action"
            onClick={handleLaunchRun}
            disabled={isPending || !selectedPlaybook}
          >
            <span>启动运行</span>
            <small>{selectedPlaybook?.name ?? "请先选择剧本"}</small>
          </button>
          <div className="settings-focus">
            <h3>{selectedPlaybook?.name ?? "未选择剧本"}</h3>
            <p>运行层会以当前 JSON 作为 `input_payload` 启动顶层剧本，适合联调 composite 串联与审批出口。</p>
            <div className="settings-focus__tags">
              <span>{selectedPlaybook?.entry_node_id || "未设入口"}</span>
              <span>{selectedPlaybook ? `${selectedPlaybook.nodes.length} 个节点` : "等待配置"}</span>
            </div>
          </div>
        </section>

        <section className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <strong>快捷动作</strong>
          </div>
          <button type="button" className="workspace-primary-action" onClick={handleStartSampleRun} disabled={isPending || !samplePlaybook}>
            <span>启动 Sample Run</span>
            <small>{samplePlaybook?.name ?? "未配置样例"}</small>
          </button>
          <button type="button" className="workspace-menu__item" onClick={handleRefresh} disabled={isPending}>
            <div>
              <strong>刷新运行列表</strong>
              <small>同步最新 run 与审批状态</small>
            </div>
          </button>
        </section>

        <section className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <strong>运行切换</strong>
          </div>
          <GraphRunList
            runs={runs}
            playbooks={playbooks}
            selectedRunId={selectedRun?.id ?? null}
            onSelectRun={(run) => {
              setSelectedRun(run);
              setSelectedNodeId(run.current_node_id ?? run.node_states[0]?.node_id ?? null);
            }}
          />
        </section>

        <section className="workspace-knowledge-card">
          <div className="workspace-knowledge-card__header">
            <strong>当前统计</strong>
            <span>{runs.length} 条</span>
          </div>
          <p>待审批 {runs.filter((run) => run.status === "waiting_for_human").length} 条，已失败 {runs.filter((run) => run.status === "failed").length} 条。</p>
          <small>建议优先点开待审批 run，审批后会通过事件流自动刷新详情。</small>
        </section>
      </aside>

      <div className="workspace-main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◎</span>
            <strong>任务驾驶舱</strong>
          </div>
          <div className="settings-topbar__note">
            <span>处理人工审批、观察节点输出、回放执行状态</span>
          </div>
        </section>
        <GraphRunCanvas
          run={selectedRun}
          playbook={canvasPlaybook}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
        />
        {statusMessage ? <p className="workspace-status workspace-status--success">{statusMessage}</p> : null}
        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </div>
      <GraphRunDetail initialRun={selectedRun} playbooks={playbooks} selectedNodeId={selectedNodeId} />
    </section>
  );
}

function sampleInitialPlaybookId(playbooks: GraphPlaybookDefinition[]) {
  return playbooks.find((playbook) => playbook.id === "graph_weekly_competitor_report")?.id ?? playbooks[0]?.id ?? "";
}
