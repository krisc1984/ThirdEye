"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import type { ManagedSkillDetail, ManagedSkillSummary } from "@/lib/api";
import { deleteManagedSkill, getManagedSkill, toggleManagedSkill, uploadSkillZip } from "@/lib/api";

type SkillsSettingsProps = {
  initialSkills: ManagedSkillSummary[];
};

const featureChips = [
  { label: "ZIP 安装", tone: "blue" },
  { label: "启用开关", tone: "orange" },
  { label: "内容预览", tone: "green" }
] as const;

export function SkillsSettings({ initialSkills }: SkillsSettingsProps) {
  const [skills, setSkills] = useState(initialSkills);
  const [selectedSkillName, setSelectedSkillName] = useState(initialSkills[0]?.name ?? "");
  const [selectedSkill, setSelectedSkill] = useState<ManagedSkillDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [uploadingName, setUploadingName] = useState<string>("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!selectedSkillName) {
      setSelectedSkill(null);
      return;
    }
    let cancelled = false;
    startTransition(async () => {
      try {
        const detail = await getManagedSkill(selectedSkillName);
        if (!cancelled) {
          setSelectedSkill(detail);
        }
      } catch (caughtError) {
        if (!cancelled) {
          setError(caughtError instanceof Error ? caughtError.message : "加载技能详情失败。");
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedSkillName]);

  const skillStats = useMemo(
    () => ({
      total: skills.length,
      enabled: skills.filter((skill) => skill.enabled).length,
      sources: new Set(skills.map((skill) => skill.source)).size
    }),
    [skills]
  );

  function handleSelectSkill(skill: ManagedSkillSummary) {
    setSelectedSkillName(skill.name);
    setError(null);
    setStatusMessage(null);
  }

  function syncSkill(nextSkill: ManagedSkillSummary | ManagedSkillDetail) {
    setSkills((current) => {
      const next = current.filter((item) => item.name !== nextSkill.name);
      return [nextSkill, ...next].sort((a, b) => a.name.localeCompare(b.name));
    });
    setSelectedSkillName(nextSkill.name);
  }

  function handleToggle(skill: ManagedSkillSummary) {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        const updated = await toggleManagedSkill(skill.name, !skill.enabled);
        syncSkill(updated);
        setSelectedSkill(updated);
        setStatusMessage(`技能「${updated.name}」已${updated.enabled ? "启用" : "停用"}。`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "切换技能状态失败。");
      }
    });
  }

  function handleDelete(skill: ManagedSkillSummary) {
    setError(null);
    setStatusMessage(null);
    startTransition(async () => {
      try {
        await deleteManagedSkill(skill.name);
        const nextSkills = skills.filter((item) => item.name !== skill.name);
        setSkills(nextSkills);
        const fallback = nextSkills[0]?.name ?? "";
        setSelectedSkillName(fallback);
        setSelectedSkill(null);
        setStatusMessage(`技能「${skill.name}」已删除。`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "删除技能失败。");
      }
    });
  }

  function handleUpload(file: File | null) {
    if (!file) return;
    setError(null);
    setStatusMessage(null);
    setUploadingName(file.name);
    startTransition(async () => {
      try {
        const result = await uploadSkillZip(file);
        syncSkill(result.installed);
        setSelectedSkill(result.installed);
        setStatusMessage(`技能包「${result.installed.name}」安装成功。`);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "上传技能包失败。");
      } finally {
        setUploadingName("");
      }
    });
  }

  return (
    <section className="settings-workspace">
      <aside className="settings-workspace__sidebar">
        <section className="workspace-panel settings-hero-card">
          <div className="workspace-brand">
            <div className="workspace-brand__mark">✦</div>
            <div>
              <strong>技能管理</strong>
              <span>Installed Skills</span>
            </div>
          </div>
          <div className="settings-hero-card__body">
            <p className="settings-hero-card__eyebrow">SKILL REGISTRY</p>
            <h1>浏览、安装、预览并控制技能生效状态</h1>
            <p>支持上传 ZIP 包安装技能，查看 SKILL.md 内容，对技能做启用、停用和删除管理。</p>
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
              <strong>技能概况</strong>
              <span>当前共 {skillStats.total} 个技能</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>总数</span>
              <strong>{skillStats.total}</strong>
            </article>
            <article className="settings-stat-card">
              <span>已启用</span>
              <strong>{skillStats.enabled}</strong>
            </article>
            <article className="settings-stat-card">
              <span>来源类型</span>
              <strong>{skillStats.sources}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>上传技能包</strong>
              <span>ZIP 包需包含 SKILL.md</span>
            </div>
          </div>
          <label className="settings-upload">
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={(event) => handleUpload(event.target.files?.[0] ?? null)}
              disabled={isPending}
            />
            <span>{uploadingName ? `上传中：${uploadingName}` : "选择 ZIP 并安装技能"}</span>
          </label>
        </section>
      </aside>

      <div className="settings-workspace__main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>技能安装中心</strong>
          </div>
          <div className="settings-topbar__note">
            <span>停用后的技能不会暴露给运行时 Agent</span>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>已安装技能</strong>
              <span>点击查看详情并管理状态</span>
            </div>
          </div>
          <div className="settings-provider-list">
            {skills.map((skill) => {
              const isSelected = skill.name === selectedSkillName;
              return (
                <article
                  key={skill.name}
                  className={`settings-provider-card ${isSelected ? "settings-provider-card--active" : ""}`}
                >
                  <div className="settings-provider-card__head">
                    <div>
                      <strong>{skill.name}</strong>
                      <span>{skill.source === "builtin" ? "内置" : "上传"}</span>
                    </div>
                    <em>{skill.enabled ? "已启用" : "已停用"}</em>
                  </div>
                  <div className="settings-provider-card__meta">
                    <span>{skill.source}</span>
                    <span>{skill.enabled ? "enabled" : "disabled"}</span>
                  </div>
                  <p className="settings-agent-card__description">{skill.description || "未提供描述。"}</p>
                  <div className="settings-provider-card__actions">
                    <button type="button" onClick={() => handleSelectSkill(skill)}>
                      查看内容
                    </button>
                    <button type="button" onClick={() => handleToggle(skill)} disabled={isPending}>
                      {skill.enabled ? "停用" : "启用"}
                    </button>
                    <button type="button" onClick={() => handleDelete(skill)} disabled={isPending || skill.source !== "uploaded"}>
                      删除
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>

      <aside className="settings-workspace__right">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>技能详情</strong>
              <span>{selectedSkill?.name ?? "未选择技能"}</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{selectedSkill?.name ?? "等待选择技能"}</h3>
            <p>{selectedSkill?.description ?? "从中间列表选择一个技能后，这里会显示技能来源、状态和完整内容预览。"}</p>
            <div className="settings-focus__tags">
              <span>{selectedSkill?.source ?? "source"}</span>
              <span>{selectedSkill?.enabled ? "enabled" : "disabled"}</span>
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>技能内容</strong>
              <span>SKILL.md 预览</span>
            </div>
          </div>
          <div className="settings-response-block settings-response-block--prompt">
            <span>SKILL.md</span>
            <code>{selectedSkill?.content ?? "暂无内容。"}</code>
          </div>
        </section>

        {statusMessage ? <p className="workspace-status workspace-status--success">{statusMessage}</p> : null}
        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </aside>
    </section>
  );
}

