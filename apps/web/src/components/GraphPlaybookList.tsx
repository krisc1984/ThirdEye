import type { GraphCompileResult, GraphPlaybookDefinition } from "@/lib/api";

type GraphPlaybookListProps = {
  playbooks: GraphPlaybookDefinition[];
  compileResults?: Record<string, GraphCompileResult>;
};

export function GraphPlaybookList({ playbooks, compileResults = {} }: GraphPlaybookListProps) {
  if (!playbooks.length) {
    return (
      <section className="workspace-panel">
        <div className="workspace-panel__header">
          <div>
            <strong>任务剧本</strong>
            <span>Graph Playbooks</span>
          </div>
        </div>
        <p className="workspace-empty">还没有可用的任务剧本。</p>
      </section>
    );
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-panel__header">
        <div>
          <p className="eyebrow">任务驾驶舱</p>
          <h1>任务剧本</h1>
        </div>
        <p className="muted">组合编译结果、entry node 和人审节点配置，作为可运行的图定义。</p>
      </div>
      <div className="list-table">
        {playbooks.map((playbook) => {
          const compile = compileResults[playbook.id];
          return (
            <article key={playbook.id} className="list-table__row">
              <div>
                <strong>{playbook.name}</strong>
                <p>{playbook.description || playbook.id}</p>
              </div>
              <div>
                <span>版本</span>
                <strong>{playbook.version}</strong>
              </div>
              <div>
                <span>入口节点</span>
                <strong>{playbook.entry_node_id}</strong>
              </div>
              <div>
                <span>编译结果</span>
                <strong>{compile?.ok ? "通过" : "需关注"}</strong>
                {compile?.warnings[0] ? <p>{compile.warnings[0]}</p> : null}
                {compile?.errors[0] ? <p>{compile.errors[0]}</p> : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
