"use client";

import { SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Item,
  ItemActions,
  ItemTitle,
  ItemContent,
  ItemDescription,
} from "@/components/ui/item";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/core/i18n/hooks";
import { useEnableSkill, useSkills } from "@/core/skills/hooks";
import type { Skill } from "@/core/skills/type";
import { env } from "@/env";

import { SettingsSection } from "./settings-section";

function SkillSetupGuide() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-6 rounded-lg border border-pink-500/20 bg-pink-50/50 dark:bg-pink-950/10 p-4 shadow-[0_0_15px_-3px_rgba(236,72,153,0.05)] backdrop-blur-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-pink-50/10 text-pink-600 dark:text-pink-400">
            🧬
          </span>
          <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
            科学研究 Skills 本地开发与扫描挂载机制
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setOpen(!open)} className="text-pink-600 dark:text-pink-400 hover:text-pink-700 dark:hover:text-pink-300 hover:bg-pink-500/10 h-7 px-2 text-xs">
          {open ? "收起指南" : "展开配置指南"}
        </Button>
      </div>
      {open && (
        <div className="mt-3 space-y-2.5 text-xs text-zinc-600 dark:text-zinc-400 border-t border-pink-500/10 pt-3 leading-relaxed">
          <p className="leading-relaxed">
            Agent Skill 是 GVIM AI 的核心科研插件系统。通过 Skills，大语言模型能完美调用特定的学术数据库接口、运行物理化学计算公式，或自动化生成实验结构报告。
          </p>
          <div className="space-y-1.5 rounded-md bg-zinc-950 dark:bg-zinc-950/60 p-2.5 border border-zinc-200 dark:border-white/5 shadow-xs">
            <div className="font-semibold text-pink-600 dark:text-pink-400">📂 自定义 Skill 本地物理挂载路径：</div>
            <p className="text-zinc-300 dark:text-zinc-400">将您手动编写的 Skill 技能文件夹直接放入 GVIM AI 根目录下的以下文件夹中：</p>
            <code className="block rounded bg-black/40 p-1.5 text-[10px] text-zinc-200 select-all font-mono leading-normal">
              E:\Demo of GVIM\deer-flow-mainnew\deer-flow-main\skills\custom\your-skill-name\
            </code>
            <p className="text-[11px] text-zinc-500">（需包含 <code className="text-zinc-400 font-mono">manifest.json</code> 提示词配置文件与 <code className="text-zinc-400 font-mono">tools/</code> 核心运行脚本）</p>
          </div>
          <div className="space-y-1">
            <div className="font-semibold text-pink-600 dark:text-pink-400">✨ AI 对话辅助极速创建捷径：</div>
            <p className="text-zinc-700 dark:text-zinc-300">您无需手动编写复杂的代码目录结构！在对话框中切换为 <b>Ultra（多智能体超强协同）模式</b>，直接输入需求：</p>
            <code className="block rounded bg-black/40 p-1.5 text-[10px] text-zinc-200 select-all font-mono leading-normal">
              帮我通过 skill-creator 技能开发一个[特定物性查询或数据绘图]的自定义技能。
            </code>
            <p className="mt-1 text-zinc-600 dark:text-zinc-400">
              系统的子代理将会自动运行，并在后台为您自动生成代码与配置文件，直接写入到上述物理目录中！
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export function SkillSettingsPage({ onClose }: { onClose?: () => void } = {}) {
  const { t } = useI18n();
  const { skills, isLoading, error } = useSkills();

  return (
    <div data-tour="skills-settings-container">
      <SettingsSection
        title={t.settings.skills.title}
        description={t.settings.skills.description}
      >
        <SkillSetupGuide />
        {isLoading ? (
          <div className="text-muted-foreground text-sm">{t.common.loading}</div>
        ) : error ? (
          <div>Error: {error.message}</div>
        ) : (
          <div className="w-full">
            <SkillSettingsList skills={skills} onClose={onClose} />
          </div>
        )}
      </SettingsSection>
    </div>
  );
}

function SkillSettingsList({
  skills,
  onClose,
}: {
  skills: Skill[];
  onClose?: () => void;
}) {
  const { t } = useI18n();
  const router = useRouter();
  const [filter, setFilter] = useState<string>("public");
  const { mutate: enableSkill } = useEnableSkill();
  const filteredSkills = useMemo(
    () => skills.filter((skill) => skill.category === filter),
    [skills, filter],
  );
  const handleCreateSkill = () => {
    onClose?.();
    router.push("/workspace/chats/new?mode=skill");
  };
  return (
    <div className="flex w-full flex-col gap-4">
      <header className="flex justify-between">
        <div className="flex gap-2">
          <Tabs defaultValue="public" onValueChange={setFilter}>
            <TabsList variant="line">
              <TabsTrigger value="public">{t.common.public}</TabsTrigger>
              <TabsTrigger value="custom">{t.common.custom}</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <div>
          <Button size="sm" onClick={handleCreateSkill}>
            <SparklesIcon className="size-4" />
            {t.settings.skills.createSkill}
          </Button>
        </div>
      </header>
      {filteredSkills.length === 0 && (
        <EmptySkill onCreateSkill={handleCreateSkill} />
      )}
      {filteredSkills.length > 0 &&
        filteredSkills.map((skill) => (
          <Item className="w-full" variant="outline" key={skill.name}>
            <ItemContent>
              <ItemTitle>
                <div className="flex items-center gap-2">{skill.name}</div>
              </ItemTitle>
              <ItemDescription className="line-clamp-4">
                {skill.description}
              </ItemDescription>
            </ItemContent>
            <ItemActions>
              <Switch
                checked={skill.enabled}
                disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                onCheckedChange={(checked) =>
                  enableSkill({ skillName: skill.name, enabled: checked })
                }
              />
            </ItemActions>
          </Item>
        ))}
    </div>
  );
}

function EmptySkill({ onCreateSkill }: { onCreateSkill: () => void }) {
  const { t } = useI18n();
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <SparklesIcon />
        </EmptyMedia>
        <EmptyTitle>{t.settings.skills.emptyTitle}</EmptyTitle>
        <EmptyDescription>
          {t.settings.skills.emptyDescription}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button onClick={onCreateSkill}>{t.settings.skills.emptyButton}</Button>
      </EmptyContent>
    </Empty>
  );
}
