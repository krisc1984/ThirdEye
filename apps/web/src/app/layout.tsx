import type { ReactNode } from "react";

import { AppNav } from "@/components/AppNav";

export const metadata = {
  title: "三眼技术评审 Agent",
  description: "通用 agent 多轮对话评审工作台。"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-frame">
          <AppNav />
          <main className="app-content">{children}</main>
        </div>
      </body>
      <style>{`
        :root {
          color-scheme: light;
          --bg: #f3efe7;
          --panel: rgba(255, 255, 255, 0.82);
          --panel-strong: #ffffff;
          --panel-soft: #f8f5ef;
          --line: rgba(33, 53, 88, 0.1);
          --line-strong: rgba(33, 53, 88, 0.18);
          --text: #22304a;
          --muted: #7c869b;
          --navy: #213558;
          --blue: #4f7cff;
          --blue-soft: #ebf1ff;
          --orange: #ff9b52;
          --orange-soft: #fff1e6;
          --green: #42b59a;
          --green-soft: #e8f8f3;
          --shadow-lg: 0 26px 80px rgba(54, 72, 98, 0.16);
          --shadow-md: 0 16px 40px rgba(54, 72, 98, 0.1);
          --shadow-sm: 0 10px 22px rgba(54, 72, 98, 0.08);
        }

        * {
          box-sizing: border-box;
        }

        html,
        body {
          margin: 0;
          min-height: 100%;
          background:
            radial-gradient(circle at top center, rgba(90, 130, 255, 0.08), transparent 22%),
            radial-gradient(circle at left 20%, rgba(255, 208, 120, 0.1), transparent 24%),
            linear-gradient(180deg, #f8f5ef 0%, #f2ede4 100%);
          color: var(--text);
          font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
        }

        a {
          color: inherit;
          text-decoration: none;
        }

        button,
        input,
        select,
        textarea {
          font: inherit;
        }

        button {
          border: none;
          background: none;
          color: inherit;
        }

        .app-frame {
          width: min(1600px, calc(100vw - 32px));
          margin: 12px auto 28px;
        }

        .app-nav {
          display: flex;
          justify-content: center;
          gap: 10px;
          padding: 10px 0 14px;
        }

        .app-nav__link {
          padding: 10px 14px;
          border-radius: 999px;
          color: var(--muted);
          border: 1px solid transparent;
          transition: 160ms ease;
        }

        .app-nav__link:hover {
          color: var(--navy);
          border-color: var(--line);
          background: rgba(255, 255, 255, 0.62);
        }

        .app-content {
          min-height: calc(100vh - 80px);
        }

        .settings-fab {
          position: fixed;
          left: 24px;
          bottom: 24px;
          z-index: 40;
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          border-radius: 999px;
          border: 1px solid rgba(33, 53, 88, 0.12);
          background: rgba(255, 255, 255, 0.9);
          box-shadow: var(--shadow-md);
          backdrop-filter: blur(18px);
          color: var(--navy);
          transition: transform 160ms ease, box-shadow 160ms ease;
        }

        .settings-fab:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg);
        }

        .settings-fab__icon {
          display: grid;
          place-items: center;
          width: 30px;
          height: 30px;
          border-radius: 999px;
          background: var(--blue-soft);
          color: var(--blue);
          font-size: 0.95rem;
        }

        .settings-fab__label {
          font-weight: 600;
          letter-spacing: 0.02em;
        }

        .workspace-shell {
          display: grid;
          grid-template-columns: 248px minmax(0, 1fr) 348px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.7);
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(18px);
        }

        .workspace-sidebar,
        .workspace-rightbar {
          display: grid;
          gap: 16px;
          align-content: start;
          align-self: start;
        }

        .workspace-main {
          display: grid;
          grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
          gap: 18px;
          min-width: 0;
          min-height: 0;
        }

        .workspace-brand,
        .workspace-panel,
        .workspace-knowledge-card,
        .workspace-composer,
        .workspace-toolbar,
        .workspace-topbar,
        .workspace-message,
        .workspace-capability,
        .workspace-project-item,
        .workspace-primary-action,
        .workspace-search,
        .workspace-menu__item {
          border: 1px solid var(--line);
          background: var(--panel);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(12px);
        }

        .workspace-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 18px;
          border-radius: 22px;
        }

        .workspace-brand__mark {
          display: grid;
          place-items: center;
          width: 44px;
          height: 44px;
          border-radius: 16px;
          background: linear-gradient(145deg, #f8fbff, #e8edfb);
          color: var(--navy);
          font-size: 1.5rem;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
        }

        .workspace-brand strong,
        .workspace-panel__header strong,
        .workspace-topbar__title strong {
          display: block;
          font-weight: 700;
        }

        .workspace-brand span,
        .workspace-panel__header span,
        .workspace-sidebar__header,
        .workspace-message__meta span,
        .workspace-empty,
        .workspace-knowledge-card p,
        .workspace-knowledge-card small,
        .workspace-project-item small,
        .workspace-menu__item small,
        .workspace-session-item small {
          color: var(--muted);
        }

        .workspace-primary-action {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          width: 100%;
          padding: 14px 16px;
          border-radius: 16px;
          background: linear-gradient(135deg, #213558, #314a78);
          color: white;
          cursor: pointer;
        }

        .workspace-primary-action small {
          padding: 2px 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.16);
          color: rgba(255, 255, 255, 0.86);
        }

        .workspace-search {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
          padding: 10px;
          border-radius: 16px;
        }

        .workspace-search input,
        .workspace-doc-search input,
        .workspace-toolbar select,
        .workspace-toolbar input,
        .workspace-composer textarea {
          width: 100%;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.74);
          color: var(--text);
        }

        .workspace-search input,
        .workspace-doc-search input {
          padding: 10px 12px;
          border-radius: 12px;
        }

        .workspace-search button,
        .workspace-doc-search button {
          width: 40px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          cursor: pointer;
        }

        .workspace-menu,
        .workspace-project-list,
        .workspace-chat,
        .workspace-session-list {
          display: grid;
          gap: 10px;
        }

        .workspace-menu__item,
        .workspace-project-item,
        .workspace-session-item {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 14px;
          border-radius: 18px;
          text-align: left;
          cursor: pointer;
        }

        .workspace-menu__item div,
        .workspace-project-item strong,
        .workspace-project-item__body {
          min-width: 0;
        }

        .workspace-project-item {
          grid-template-columns: auto minmax(0, 1fr) auto;
        }

        .workspace-project-item__body {
          display: grid;
          gap: 2px;
        }

        .workspace-project-item__delete {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 999px;
          border: 1px solid rgba(255, 93, 84, 0.12);
          background: rgba(255, 93, 84, 0.08);
          color: #c4544d;
          cursor: pointer;
        }

        .workspace-project-item__delete:hover {
          background: rgba(255, 93, 84, 0.14);
        }

        .workspace-menu__item strong,
        .workspace-project-item strong,
        .workspace-session-item strong,
        .workspace-summary h3,
        .workspace-capability strong,
        .workspace-message__body strong,
        .workspace-doc-item__body strong,
        .workspace-finding__header strong {
          font-weight: 600;
        }

        .workspace-menu__item--active,
        .workspace-project-item--active,
        .workspace-session-item--active {
          border-color: rgba(79, 124, 255, 0.25);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(235, 241, 255, 0.9));
        }

        .workspace-sidebar__section {
          display: grid;
          gap: 12px;
        }

        .workspace-sidebar__header,
        .workspace-panel__header,
        .workspace-topbar,
        .workspace-composer__footer,
        .workspace-summary__footer,
        .workspace-doc-group__title,
        .workspace-message__meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .workspace-knowledge-card {
          padding: 18px;
          border-radius: 22px;
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(240, 246, 255, 0.84)),
            radial-gradient(circle at right bottom, rgba(79, 124, 255, 0.18), transparent 35%);
        }

        .workspace-knowledge-card__header {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
          margin-bottom: 10px;
        }

        .workspace-knowledge-card__header span {
          color: #37a96b;
          font-size: 0.88rem;
        }

        .workspace-knowledge-card button,
        .workspace-upload,
        .workspace-summary__footer button,
        .workspace-finding button {
          padding: 10px 14px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.85);
          cursor: pointer;
        }

        .workspace-topbar {
          padding: 16px 20px;
          border-radius: 22px;
        }

        .workspace-topbar__title,
        .workspace-topbar__actions {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .workspace-topbar__logo {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: var(--blue-soft);
          color: var(--blue);
        }

        .workspace-topbar__actions button {
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.75);
          border: 1px solid var(--line);
          cursor: pointer;
        }

        .workspace-hero {
          display: grid;
          justify-items: center;
          gap: 10px;
          padding: 18px 12px 2px;
          text-align: center;
        }

        .workspace-hero h1 {
          margin: 0;
          font-size: clamp(2rem, 3.2vw, 3.2rem);
          letter-spacing: -0.04em;
        }

        .workspace-hero p {
          margin: 0;
          color: var(--muted);
        }

        .workspace-orbit {
          position: relative;
          width: 220px;
          height: 140px;
        }

        .workspace-orbit__ring,
        .workspace-orbit__core,
        .workspace-orbit__node {
          position: absolute;
          border-radius: 999px;
        }

        .workspace-orbit__ring {
          inset: 14px;
          border: 1px solid rgba(79, 124, 255, 0.16);
        }

        .workspace-orbit__ring--outer {
          transform: rotate(16deg);
        }

        .workspace-orbit__ring--inner {
          inset: 30px 18px;
          transform: rotate(-18deg);
        }

        .workspace-orbit__core,
        .workspace-orbit__node {
          display: grid;
          place-items: center;
          background:
            radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(176, 200, 255, 0.75)),
            linear-gradient(180deg, #24406a, #1c2c4a);
          color: white;
          box-shadow:
            0 10px 24px rgba(62, 95, 160, 0.28),
            inset 0 2px 10px rgba(255, 255, 255, 0.18);
        }

        .workspace-orbit__core {
          inset: 34px 76px;
          font-size: 2rem;
        }

        .workspace-orbit__node {
          width: 52px;
          height: 52px;
          top: 60px;
          font-size: 1.15rem;
        }

        .workspace-orbit__node--left {
          left: 28px;
        }

        .workspace-orbit__node--right {
          right: 28px;
        }

        .workspace-capabilities {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }

        .workspace-capability {
          padding: 18px;
          border-radius: 22px;
        }

        .workspace-capability__badge {
          display: inline-grid;
          place-items: center;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          margin-bottom: 14px;
        }

        .workspace-capability--blue .workspace-capability__badge {
          color: var(--blue);
          background: var(--blue-soft);
        }

        .workspace-capability--orange .workspace-capability__badge {
          color: var(--orange);
          background: var(--orange-soft);
        }

        .workspace-capability--green .workspace-capability__badge {
          color: var(--green);
          background: var(--green-soft);
        }

        .workspace-capability p,
        .workspace-summary p,
        .workspace-summary li,
        .workspace-message__body p,
        .workspace-finding p {
          color: var(--muted);
          line-height: 1.7;
        }

        .workspace-toolbar {
          display: grid;
          grid-template-columns: minmax(0, 1fr);
          gap: 12px;
          padding: 14px;
          border-radius: 18px;
        }

        .workspace-project-creator {
          display: grid;
          gap: 10px;
          padding: 12px;
          border-radius: 16px;
          border: 1px dashed var(--line-strong);
          background: rgba(255, 255, 255, 0.56);
        }

        .workspace-project-creator input {
          width: 100%;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
          color: var(--text);
        }

        .workspace-project-creator button,
        .workspace-sidebar__header button {
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
          cursor: pointer;
        }

        .workspace-toolbar label {
          display: grid;
          gap: 8px;
          min-width: 0;
        }

        .workspace-toolbar__summary {
          display: grid;
          gap: 6px;
        }

        .workspace-toolbar__summary strong {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text);
        }

        .workspace-toolbar span {
          font-size: 0.85rem;
          color: var(--muted);
        }

        .workspace-toolbar select {
          padding: 10px 12px;
          border-radius: 12px;
        }

        .workspace-chat {
          align-content: start;
          min-height: 0;
          max-height: min(52vh, 760px);
          padding-right: 4px;
          overflow: auto;
        }

        .workspace-message {
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          gap: 14px;
          padding: 16px;
          border-radius: 24px;
        }

        .workspace-message--user {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(247, 245, 240, 0.9));
        }

        .workspace-message--assistant {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.94));
        }

        .workspace-message--welcome {
          border-style: dashed;
        }

        .workspace-avatar {
          display: grid;
          place-items: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(180deg, #eef3ff, #dde8fb);
          color: var(--navy);
          font-size: 0.95rem;
          font-weight: 700;
        }

        .workspace-message__body p {
          margin: 8px 0 0;
          white-space: pre-wrap;
        }

        .workspace-starters,
        .workspace-finding-cards,
        .workspace-doc-tabs,
        .workspace-composer__actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .workspace-starters button,
        .workspace-doc-tabs button,
        .workspace-composer__actions button {
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-finding-cards {
          margin-top: 14px;
        }

        .workspace-finding {
          flex: 1 1 180px;
          min-width: 0;
          padding: 14px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.92);
        }

        .workspace-finding--blue {
          background: linear-gradient(180deg, rgba(239, 245, 255, 0.9), rgba(255, 255, 255, 0.95));
        }

        .workspace-finding--orange {
          background: linear-gradient(180deg, rgba(255, 244, 233, 0.92), rgba(255, 255, 255, 0.95));
        }

        .workspace-finding--green {
          background: linear-gradient(180deg, rgba(236, 251, 246, 0.92), rgba(255, 255, 255, 0.95));
        }

        .workspace-composer {
          padding: 16px;
          border-radius: 24px;
        }

        .workspace-skill-hints {
          display: grid;
          gap: 10px;
          margin-bottom: 12px;
        }

        .workspace-skill-hints > span {
          font-size: 0.82rem;
          color: var(--muted);
        }

        .workspace-skill-hints__list {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .workspace-skill-hints__list button {
          padding: 8px 12px;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-composer textarea {
          min-height: 116px;
          padding: 14px 16px;
          border-radius: 16px;
          resize: vertical;
        }

        .workspace-composer__submit {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }

        .workspace-composer__submit span {
          color: var(--muted);
          font-size: 0.92rem;
        }

        .workspace-composer__control {
          display: grid;
          gap: 6px;
        }

        .workspace-composer__control span {
          font-size: 0.78rem;
          color: var(--muted);
        }

        .workspace-composer__control select {
          min-width: 148px;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          color: var(--text);
        }

        .workspace-composer__submit button {
          display: grid;
          place-items: center;
          width: 44px;
          height: 44px;
          border-radius: 14px;
          background: linear-gradient(135deg, #4477f8, #1f56dd);
          color: white;
          cursor: pointer;
          box-shadow: 0 12px 24px rgba(68, 119, 248, 0.3);
        }

        .workspace-composer__submit button:disabled {
          cursor: wait;
          opacity: 0.6;
        }

        .workspace-panel {
          display: grid;
          gap: 14px;
          padding: 18px;
          border-radius: 24px;
          align-content: start;
        }

        .workspace-panel--summary {
          background:
            linear-gradient(180deg, rgba(255, 252, 243, 0.95), rgba(255, 249, 232, 0.9)),
            radial-gradient(circle at top right, rgba(255, 196, 82, 0.12), transparent 32%);
        }

        .workspace-doc-tabs {
          gap: 12px;
        }

        .workspace-doc-tabs__active {
          color: var(--blue);
          border-color: rgba(79, 124, 255, 0.2);
          background: rgba(235, 241, 255, 0.9);
        }

        .workspace-doc-search {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
        }

        .workspace-doc-tree,
        .workspace-doc-group {
          display: grid;
          gap: 10px;
        }

        .workspace-doc-item {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
        }

        .workspace-doc-item__icon {
          display: grid;
          place-items: center;
          min-width: 38px;
          height: 38px;
          padding: 0 10px;
          border-radius: 12px;
          font-size: 0.7rem;
          font-weight: 700;
        }

        .workspace-doc-item__icon--pdf {
          background: #fff0ef;
          color: #ff5e57;
        }

        .workspace-doc-item__icon--doc {
          background: #ecf3ff;
          color: #4f7cff;
        }

        .workspace-doc-item__icon--uml {
          background: #f5f2ff;
          color: #7a67f8;
        }

        .workspace-doc-item__icon--sheet {
          background: #e8f8f3;
          color: #22a16f;
        }

        .workspace-doc-item__body small,
        .workspace-doc-item time {
          color: var(--muted);
        }

        .workspace-upload {
          width: 100%;
        }

        .workspace-summary h3 {
          margin: 0 0 8px;
          font-size: 1rem;
        }

        .workspace-summary p,
        .workspace-summary ul {
          margin: 0 0 16px;
          padding-left: 18px;
        }

        .workspace-summary p {
          padding-left: 0;
        }

        .workspace-summary__footer {
          padding-top: 8px;
          border-top: 1px solid rgba(33, 53, 88, 0.08);
        }

        .workspace-summary__footer button {
          background: rgba(255, 184, 77, 0.14);
          color: #d48a18;
          border-color: rgba(255, 184, 77, 0.18);
        }

        .workspace-session-item {
          display: grid;
          gap: 4px;
          min-width: 0;
        }

        .workspace-session-item strong,
        .workspace-session-item small {
          display: block;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .workspace-status {
          margin: 0;
          padding: 12px 14px;
          border-radius: 14px;
        }

        .workspace-status button {
          margin-left: 10px;
          padding: 6px 10px;
          border-radius: 10px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-status--error {
          color: #b34b46;
          background: rgba(255, 93, 84, 0.09);
          border: 1px solid rgba(255, 93, 84, 0.14);
        }

        .settings-workspace {
          display: grid;
          grid-template-columns: 300px minmax(0, 1fr) 340px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.7);
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(18px);
        }

        .settings-workspace__sidebar,
        .settings-workspace__right,
        .settings-workspace__main {
          display: grid;
          gap: 16px;
          align-content: start;
          min-width: 0;
        }

        .settings-hero-card {
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(240, 246, 255, 0.84)),
            radial-gradient(circle at right bottom, rgba(79, 124, 255, 0.14), transparent 38%);
        }

        .settings-hero-card__body {
          display: grid;
          gap: 10px;
        }

        .settings-hero-card__eyebrow {
          margin: 0;
          font-size: 0.78rem;
          letter-spacing: 0.24em;
          color: var(--blue);
        }

        .settings-hero-card__body h1,
        .settings-focus h3 {
          margin: 0;
          line-height: 1.15;
          letter-spacing: -0.04em;
        }

        .settings-hero-card__body h1 {
          font-size: clamp(1.8rem, 2.2vw, 2.6rem);
        }

        .settings-hero-card__body p,
        .settings-focus p,
        .settings-test-result p {
          margin: 0;
          color: var(--muted);
          line-height: 1.75;
        }

        .settings-chip-row,
        .settings-focus__tags,
        .settings-capability-list {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .settings-chip,
        .settings-focus__tags span,
        .settings-capability-list span {
          display: inline-flex;
          align-items: center;
          padding: 8px 12px;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
          font-size: 0.85rem;
        }

        .settings-chip--blue {
          color: var(--blue);
          background: rgba(235, 241, 255, 0.92);
        }

        .settings-chip--orange {
          color: #da7f2d;
          background: rgba(255, 241, 230, 0.9);
        }

        .settings-chip--green {
          color: #2f9a7e;
          background: rgba(232, 248, 243, 0.92);
        }

        .settings-stat-grid,
        .settings-provider-list {
          display: grid;
          gap: 12px;
        }

        .settings-stat-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .settings-stat-card,
        .settings-provider-card,
        .settings-response-block {
          border: 1px solid var(--line);
          background: var(--panel);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(12px);
        }

        .settings-stat-card {
          display: grid;
          gap: 6px;
          padding: 14px 16px;
          border-radius: 18px;
        }

        .settings-stat-card span,
        .settings-provider-card__head span,
        .settings-provider-card__meta span,
        .settings-response-block span,
        .settings-toggle span,
        .settings-topbar__note span {
          color: var(--muted);
        }

        .settings-stat-card strong {
          font-size: 1.6rem;
        }

        .settings-provider-card {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 22px;
        }

        .settings-provider-card--active {
          border-color: rgba(79, 124, 255, 0.22);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(235, 241, 255, 0.9));
        }

        .settings-provider-card__head,
        .settings-provider-card__actions,
        .settings-form-actions,
        .settings-topbar__note {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .settings-provider-card__head em {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.8);
          color: var(--navy);
          font-style: normal;
          font-size: 0.82rem;
        }

        .settings-provider-card__meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .settings-provider-card__meta span {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.72);
        }

        .settings-provider-card__actions button,
        .settings-cta {
          padding: 10px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          cursor: pointer;
        }

        .settings-provider-card__actions button {
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-topbar {
          padding: 16px 20px;
          border-radius: 22px;
        }

        .settings-form-panel {
          gap: 18px;
        }

        .settings-form-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        .settings-field {
          display: grid;
          gap: 8px;
          min-width: 0;
        }

        .settings-field span {
          font-size: 0.9rem;
          color: var(--muted);
        }

        .settings-field input,
        .settings-field select {
          width: 100%;
          padding: 12px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          color: var(--text);
        }

        .settings-field--full {
          grid-column: 1 / -1;
        }

        .settings-toggle {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
        }

        .settings-toggle input {
          width: 18px;
          height: 18px;
          margin: 0;
        }

        .settings-toggle div {
          display: grid;
          gap: 4px;
        }

        .settings-cta--primary {
          background: linear-gradient(135deg, #213558, #314a78);
          color: white;
          box-shadow: 0 14px 30px rgba(33, 53, 88, 0.2);
        }

        .settings-cta--secondary {
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-cta:disabled,
        .settings-provider-card__actions button:disabled {
          opacity: 0.6;
          cursor: wait;
        }

        .settings-focus {
          display: grid;
          gap: 12px;
        }

        .settings-test-result {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 20px;
        }

        .settings-test-result--success {
          background: linear-gradient(180deg, rgba(236, 251, 246, 0.92), rgba(255, 255, 255, 0.95));
          border: 1px solid rgba(66, 181, 154, 0.18);
        }

        .settings-test-result--error {
          background: linear-gradient(180deg, rgba(255, 239, 238, 0.95), rgba(255, 255, 255, 0.95));
          border: 1px solid rgba(255, 93, 84, 0.18);
        }

        .settings-response-block {
          display: grid;
          gap: 8px;
          padding: 14px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-response-block code {
          white-space: pre-wrap;
          word-break: break-word;
          color: var(--navy);
        }

        .panel,
        .subpanel,
        .page-stack,
        .hero,
        .main-content,
        .review-grid,
        .chat-thread,
        .chat-bubble,
        .info-grid,
        .status,
        .button,
        .field,
        .form-grid,
        .action-row,
        .rule-list,
        .plain-list,
        .evidence-list,
        .list-table,
        .list-table__row,
        .stats-grid,
        .stat-card,
        .debug-details,
        .debug-grid,
        .token-list,
        .tab-row,
        .code-block,
        .eyebrow,
        .muted {
          font-family: inherit;
        }

        @media (max-width: 1280px) {
          .workspace-shell {
            grid-template-columns: 220px minmax(0, 1fr) 320px;
          }

          .settings-workspace {
            grid-template-columns: 260px minmax(0, 1fr) 300px;
          }
        }

        @media (max-width: 1100px) {
          .workspace-shell {
            grid-template-columns: 1fr;
          }

          .settings-workspace {
            grid-template-columns: 1fr;
          }

          .workspace-sidebar,
          .workspace-rightbar,
          .settings-workspace__sidebar,
          .settings-workspace__right {
            grid-template-columns: 1fr;
            align-self: stretch;
          }

          .workspace-main,
          .settings-workspace__main {
            order: -1;
          }

          .workspace-chat {
            max-height: none;
          }
        }

        @media (max-width: 760px) {
          .app-frame {
            width: min(100vw - 12px, 1600px);
            margin-top: 6px;
          }

          .app-nav {
            justify-content: flex-start;
            overflow: auto;
            padding-bottom: 10px;
          }

          .settings-fab {
            left: 12px;
            bottom: 12px;
            padding: 10px 14px;
          }

          .workspace-shell,
          .settings-workspace {
            padding: 10px;
            border-radius: 22px;
          }

          .workspace-capabilities,
          .workspace-toolbar,
          .settings-stat-grid,
          .settings-form-grid {
            grid-template-columns: 1fr;
          }

          .workspace-composer__footer,
          .workspace-topbar,
          .workspace-panel__header,
          .settings-provider-card__head,
          .settings-provider-card__actions,
          .settings-form-actions,
          .settings-topbar__note {
            align-items: flex-start;
            flex-direction: column;
          }

          .workspace-message {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </html>
  );
}
