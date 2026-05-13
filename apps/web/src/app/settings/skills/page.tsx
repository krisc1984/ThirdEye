import { SettingsSectionTabs } from "@/components/SettingsSectionTabs";
import { SkillsSettings } from "@/components/SkillsSettings";
import { listManagedSkills } from "@/lib/api";

export default async function SkillsSettingsPage() {
  const skills = await listManagedSkills();

  return (
    <div className="page-stack">
      <SettingsSectionTabs active="skills" />
      <SkillsSettings initialSkills={skills} />
    </div>
  );
}
