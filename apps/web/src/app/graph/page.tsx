import Link from "next/link";

import {
  compileGraphPlaybook,
  listGraphCapabilities,
  listGraphComposites,
  listGraphPlaybooks,
  listGraphRuns
} from "@/lib/api";

export default async function GraphOverviewPage() {
  const [capabilities, composites, playbooks, runs] = await Promise.all([
    listGraphCapabilities(),
    listGraphComposites(),
    listGraphPlaybooks(),
    listGraphRuns()
  ]);
  const compileResults = await Promise.all(playbooks.map((playbook) => compileGraphPlaybook(playbook.id)));
  const warningCount = compileResults.reduce((total, result) => total + result.warnings.length, 0);
  const waitingRuns = runs.filter((run) => run.status === "waiting_for_human");
  const failedRuns = runs.filter((run) => run.status === "failed");
  const samplePlaybook =
    playbooks.find((playbook) => playbook.id === "graph_weekly_competitor_report") ?? playbooks[0] ?? null;

  return (
    <section className="workspace-shell">
      <aside className="workspace-sidebar">
        <section className="workspace-brand">
          <div className="workspace-brand__mark">◎</div>
          <div>
            <strong>任务驾驶舱</strong>
            <span>Skill Graph 2.0</span>
          </div>
        </section>

        <section className="workspace-sidebar__section">
          <div className="workspace-sidebar__header">
            <strong>入口导航</strong>
          </div>
          <div className="workspace-menu">
            <Link href="/graph" className="workspace-menu__item workspace-menu__item--active">
              <div>
                <strong>总览</strong>
                <small>看图谱健康度与待处理事项</small>
              </div>
            </Link>
            <Link href="/graph/playbooks" className="workspace-menu__item">
              <div>
                <strong>图谱剧本</strong>
                <small>查看 Graph Playbook 定义</small>
              </div>
            </Link>
            <Link href="/graph/runs" className="workspace-menu__item">
              <div>
                <strong>运行台</strong>
                <small>处理人工审批与运行跟踪</small>
              </div>
            </Link>
            <Link href="/graph/capabilities" className="workspace-menu__item">
              <div>
                <strong>能力注册</strong>
                <small>浏览 capability 清单</small>
              </div>
            </Link>
            <Link href="/graph/composites" className="workspace-menu__item">
              <div>
                <strong>组合链路</strong>
                <small>查看 composite 编排</small>
              </div>
            </Link>
          </div>
        </section>

        <section className="workspace-knowledge-card">
          <div className="workspace-knowledge-card__header">
            <strong>推荐样例</strong>
            <span>{samplePlaybook ? "已就绪" : "未配置"}</span>
          </div>
          <p>{samplePlaybook?.name ?? "暂无默认图谱剧本"}</p>
          <small>建议从运行台启动 sample run，体验暂停审批和恢复执行的完整链路。</small>
        </section>
      </aside>

      <div className="workspace-main">
        <section className="workspace-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>Graph Playbook 运行总览</strong>
          </div>
          <div className="workspace-topbar__actions">
            <Link href="/graph/runs">查看运行台</Link>
            <Link href="/graph/playbooks">查看图谱剧本</Link>
          </div>
        </section>

        <section className="workspace-hero">
          <div className="workspace-orbit">
            <div className="workspace-orbit__ring workspace-orbit__ring--outer" />
            <div className="workspace-orbit__ring workspace-orbit__ring--inner" />
            <div className="workspace-orbit__core">图</div>
            <div className="workspace-orbit__node workspace-orbit__node--left">批</div>
            <div className="workspace-orbit__node workspace-orbit__node--right">审</div>
          </div>
          <h1>让复杂流程在关键节点等你拍板</h1>
          <p>当前实现聚焦 chain composite、人工审批、事件流回放和本地 JSON 工件持久化。</p>
        </section>

        <section className="workspace-capabilities">
          <article className="workspace-capability workspace-capability--blue">
            <span className="workspace-capability__badge">能</span>
            <strong>能力原子</strong>
            <p>{capabilities.length} 个 capability 已注册，负责最小动作执行。</p>
          </article>
          <article className="workspace-capability workspace-capability--orange">
            <span className="workspace-capability__badge">链</span>
            <strong>组合编排</strong>
            <p>{composites.length} 个 chain composite，按依赖顺序把动作串成有界任务。</p>
          </article>
          <article className="workspace-capability workspace-capability--green">
            <span className="workspace-capability__badge">跑</span>
            <strong>运行态</strong>
            <p>{runs.length} 个 run 已记录，支持暂停审批、恢复执行和快照回放。</p>
          </article>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>图谱健康度</strong>
              <span>聚焦编译告警、人工阻塞和失败运行</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>图谱剧本</span>
              <strong>{playbooks.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>待审批</span>
              <strong>{waitingRuns.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>失败运行</span>
              <strong>{failedRuns.length}</strong>
            </article>
            <article className="settings-stat-card">
              <span>编译告警</span>
              <strong>{warningCount}</strong>
            </article>
          </div>
        </section>
      </div>

      <aside className="workspace-rightbar">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>驾驶建议</strong>
              <span>按 P0 实现现状整理</span>
            </div>
          </div>
          <div className="workspace-summary">
            <h3>一、当前重点</h3>
            <p>先处理 `waiting_for_human` 的运行，再回头看 compile warning。这样最能降低阻塞时间。</p>
            <h3>二、推荐顺序</h3>
            <ul>
              <li>先打开运行台，处理待审批 run</li>
              <li>再检查 Graph Playbook 的编译告警</li>
              <li>最后回到 capability 与 composite 做结构清理</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>快速入口</strong>
              <span>直接跳到最常用页面</span>
            </div>
          </div>
          <div className="workspace-session-list">
            <Link href="/graph/runs" className="workspace-session-item">
              <strong>运行台</strong>
              <small>查看状态、审批和节点输出</small>
            </Link>
            <Link href="/graph/playbooks" className="workspace-session-item">
              <strong>图谱剧本</strong>
              <small>查看编译结果与入口节点</small>
            </Link>
            <Link href="/graph/capabilities" className="workspace-session-item">
              <strong>能力注册</strong>
              <small>核对 capability 动作与可用性</small>
            </Link>
          </div>
        </section>
      </aside>
    </section>
  );
}
