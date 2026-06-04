"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { toggleMcpServer, type McpServerConfig } from "@/lib/api";

type McpSettingsProps = {
  initialServices: McpServerConfig[];
};

const featureChips = [
  { label: "外部工具接入", tone: "blue" },
  { label: "连接状态可视", tone: "orange" },
  { label: "后续可接 API", tone: "green" }
] as const;

const transportLabels = {
  stdio: "STDIO",
  streamable_http: "Streamable HTTP",
  sse: "SSE"
} as const;

const scopeLabels = {
  global: "全局用户",
  project: "项目级"
} as const;

const statusLabels = {
  connected: "Connected",
  idle: "Idle",
  attention: "需要处理"
} as const;

export function McpSettings({ initialServices }: McpSettingsProps) {
  const [services, setServices] = useState(initialServices);

  const stats = useMemo(
    () => ({
      total: services.length,
      connected: services.filter((service) => service.status === "connected").length,
      attention: services.filter((service) => service.status === "attention").length
    }),
    [services]
  );

  const groupedServices = useMemo(
    () => ({
      global: services.filter((service) => service.scope === "global"),
      project: services.filter((service) => service.scope === "project")
    }),
    [services]
  );

  async function toggleServiceEnabled(service: McpServerConfig) {
    const updated = await toggleMcpServer(service.id, !service.enabled);
    setServices((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  function renderServiceRow(service: McpServerConfig) {
    return (
      <article key={service.id} className="mcp-service-row">
        <div className="mcp-service-row__main">
          <div className="mcp-service-row__title">
            <strong>{service.name}</strong>
            <span className={`mcp-status-badge mcp-status-badge--${service.status}`}>{statusLabels[service.status]}</span>
          </div>
          <div className="settings-provider-card__meta">
            <span>{transportLabels[service.transport]}</span>
            <span>{scopeLabels[service.scope]}</span>
            <span>{service.enabled ? "已启用" : "已停用"}</span>
          </div>
          <p className="settings-agent-card__description">
            {service.transport === "stdio"
              ? `${service.command ?? ""} ${(service.args ?? []).join(" ")}`
              : service.endpoint ?? service.description}
          </p>
        </div>
        <div className="mcp-service-row__actions">
          <button type="button" className="mcp-icon-button" aria-label={`配置 ${service.name}`}>
            ⚙
          </button>
          <label className="mcp-switch" aria-label={`切换 ${service.name} 启用状态`}>
            <input
              type="checkbox"
              checked={service.enabled}
              onChange={() => {
                void toggleServiceEnabled(service);
              }}
            />
            <span className="mcp-switch__track">
              <span className="mcp-switch__thumb" />
            </span>
          </label>
        </div>
      </article>
    );
  }

  return (
    <section className="settings-workspace">
      <aside className="settings-workspace__sidebar">
        <section className="workspace-panel settings-hero-card">
          <div className="workspace-brand">
            <div className="workspace-brand__mark">M</div>
            <div>
              <strong>MCP 服务</strong>
              <span>Managed Connectors</span>
            </div>
          </div>
          <div className="settings-hero-card__body">
            <p className="settings-hero-card__eyebrow">MCP SERVICE HUB</p>
            <h1>在设置中心直接管理外部工具与数据源接入</h1>
            <p>先按评审工作台的风格提供管理面板，支持查看连接状态、启停服务，并进入新增服务页完成自定义配置。</p>
          </div>
          <div className="settings-chip-row">
            {featureChips.map((chip) => (
              <span key={chip.label} className={`settings-chip settings-chip--${chip.tone}`}>
                {chip.label}
              </span>
            ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>服务概况</strong>
              <span>当前已接入 {stats.total} 个 MCP 服务</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>服务总数</span>
              <strong>{stats.total}</strong>
            </article>
            <article className="settings-stat-card">
              <span>当前已连接</span>
              <strong>{stats.connected}</strong>
            </article>
            <article className="settings-stat-card">
              <span>需要处理</span>
              <strong>{stats.attention}</strong>
            </article>
          </div>
        </section>
      </aside>

      <div className="settings-workspace__main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>MCP 服务管理台</strong>
          </div>
          <div className="workspace-topbar__actions">
            <Link href="/settings/mcp/new" className="settings-cta settings-cta--primary">
              + 添加服务
            </Link>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>全局用户</strong>
              <span>面向所有会话默认可见的工具连接</span>
            </div>
          </div>
          <div className="mcp-service-list">
            {groupedServices.global.map(renderServiceRow)}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>项目级服务</strong>
              <span>按工作区或业务上下文启用的定向连接</span>
            </div>
          </div>
          <div className="mcp-service-list">
            {groupedServices.project.length ? (
              groupedServices.project.map(renderServiceRow)
            ) : (
              <p className="workspace-empty">还没有项目级 MCP 服务，先从右上角添加一个。</p>
            )}
          </div>
        </section>
      </div>

      <aside className="settings-workspace__right">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>接入说明</strong>
              <span>和评审工作台保持同一视觉密度</span>
            </div>
          </div>
          <div className="workspace-summary">
            <h3>一、当前范围</h3>
            <p>本轮先完成设置内的 MCP 管理页与新增服务页 UI，数据通过本地 mock 驱动，便于后续无缝替换成真实接口。</p>
            <h3>二、后续扩展</h3>
            <ul>
              <li>可补充真实连接测试与重连动作</li>
              <li>可接入编辑、删除、审计记录和最近错误</li>
              <li>可在服务级别展示依赖环境变量健康度</li>
            </ul>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>传输类型</strong>
              <span>当前页面覆盖三类 MCP 接入方式</span>
            </div>
          </div>
          <div className="settings-focus__tags">
            <span>STDIO</span>
            <span>Streamable HTTP</span>
            <span>SSE</span>
          </div>
        </section>
      </aside>
    </section>
  );
}
