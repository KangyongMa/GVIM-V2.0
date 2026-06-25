"use client";

import { useEffect, useState, type ReactNode } from "react";
import { 
  EyeIcon, 
  EyeOffIcon, 
  SaveIcon,
  AtomIcon,
  BeakerIcon,
  BookOpenIcon,
  CpuIcon,
  WrenchIcon,
  SparklesIcon,
  SearchIcon,
  FileTextIcon,
  GithubIcon,
  GlobeIcon,
  ZapIcon,
  BinaryIcon,
  FingerprintIcon
} from "lucide-react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetch, getCsrfHeaders } from "@/core/api/fetcher";
import { useI18n } from "@/core/i18n/hooks";
import { SettingsSection } from "./settings-section";

interface ApiKeys {
  DEEPSEEK_API_KEY: string;
  DASHSCOPE_API_KEY: string;
  GLM_API_KEY: string;
  ANTHROPIC_API_KEY: string;
  OPENAI_API_KEY: string;
  GEMINI_API_KEY: string;
  MP_API_KEY: string;
  CITRINATION_API_KEY: string;
  SEMANTIC_SCHOLAR_API_KEY: string;
  NCBI_API_KEY: string;
  MINERU_API_TOKEN: string;
  GITHUB_TOKEN: string;
  HF_TOKEN: string;
  SERPER_API_KEY: string;
  TAVILY_API_KEY: string;
  JINA_API_KEY: string;
}

const defaultKeys: ApiKeys = {
  DEEPSEEK_API_KEY: "",
  DASHSCOPE_API_KEY: "",
  GLM_API_KEY: "",
  ANTHROPIC_API_KEY: "",
  OPENAI_API_KEY: "",
  GEMINI_API_KEY: "",
  MP_API_KEY: "",
  CITRINATION_API_KEY: "",
  SEMANTIC_SCHOLAR_API_KEY: "",
  NCBI_API_KEY: "",
  MINERU_API_TOKEN: "",
  GITHUB_TOKEN: "",
  HF_TOKEN: "",
  SERPER_API_KEY: "",
  TAVILY_API_KEY: "",
  JINA_API_KEY: "",
};

export function ModelSettingsPage() {
  const { t, locale } = useI18n();
  const queryClient = useQueryClient();
  const [keys, setKeys] = useState<ApiKeys>(defaultKeys);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const isZh = locale === "zh-CN";
  const activeText = isZh ? "已配置" : "Active";
  const inactiveText = isZh ? "未配置" : "Inactive";

  useEffect(() => {
    async function loadKeys() {
      try {
        const res = await fetch("/api/models/config/keys");
        if (res.ok) {
          const data = await res.json();
          setKeys({ ...defaultKeys, ...data.keys });
        } else {
          toast.error(t.settings.models.saveFailed);
        }
      } catch (err) {
        console.error("Failed to load keys", err);
      } finally {
        setLoading(false);
      }
    }
    loadKeys();
  }, [t.settings.models.saveFailed]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch("/api/models/config/keys", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...getCsrfHeaders(),
        },
        body: JSON.stringify({ keys }),
      });

      if (res.ok) {
        const data = await res.json();
        setKeys({ ...defaultKeys, ...data.keys });
        toast.success(t.settings.models.saved);
        queryClient.invalidateQueries({ queryKey: ["models"] });
      } else {
        toast.error(t.settings.models.saveFailed);
      }
    } catch (err) {
      toast.error(t.settings.models.saveFailed);
    } finally {
      setSaving(false);
    }
  };

  const toggleVisibility = (key: keyof ApiKeys) => {
    setVisibleKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleKeyChange = (key: keyof ApiKeys, value: string) => {
    setKeys((prev) => ({ ...prev, [key]: value }));
  };

  const isKeyConfigured = (keyName: keyof ApiKeys) => {
    const val = keys[keyName];
    return val && val.trim() !== "";
  };

  if (loading) {
    return <div className="text-muted-foreground text-sm p-4">{t.common.loading}</div>;
  }

  const renderKeyField = (fieldName: keyof ApiKeys, label: string, fieldIcon: ReactNode) => {
    const isVisible = visibleKeys[fieldName] || false;
    const isConfigured = isKeyConfigured(fieldName);
    return (
      <div key={fieldName} className="space-y-2 group/field">
        <div className="flex items-center justify-between min-h-[2.25rem] py-0.5">
          <div className="flex items-center gap-1.5 text-muted-foreground group-hover/field:text-foreground transition-colors duration-300">
            <span className="shrink-0">{fieldIcon}</span>
            <label className="text-xs font-semibold tracking-wide cursor-pointer leading-tight">{label}</label>
          </div>
          <div className="shrink-0">
            {isConfigured ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[9px] font-bold text-emerald-500 ring-1 ring-inset ring-emerald-500/20 shadow-sm shadow-emerald-500/5 transition-all duration-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {activeText}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-0.5 text-[9px] font-bold text-muted-foreground/80 transition-all duration-300">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
                {inactiveText}
              </span>
            )}
          </div>
        </div>
        <div className="relative flex items-center group">
          <Input
            type={isVisible ? "text" : "password"}
            placeholder={t.settings.models.placeholder}
            value={keys[fieldName] || ""}
            onChange={(e) => handleKeyChange(fieldName, e.target.value)}
            className="pr-10 border-muted-foreground/20 focus-visible:ring-primary/45 focus-visible:border-primary/40 focus:shadow-sm shadow-primary/5 transition-all duration-300"
          />
          <button
            type="button"
            onClick={() => toggleVisibility(fieldName)}
            className="absolute right-3 text-muted-foreground hover:text-foreground opacity-50 group-hover:opacity-100 hover:scale-110 active:scale-95 transition-all duration-300"
          >
            {isVisible ? <EyeOffIcon className="size-4" /> : <EyeIcon className="size-4" />}
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8 pb-10">
      <SettingsSection
        title={t.settings.models.title}
        description={t.settings.models.description}
      >
        <form onSubmit={handleSave} className="space-y-6">
          {/* Card 1: Chemistry & Materials Compute */}
          <Card data-tour="science-keys-card" className="overflow-hidden border-border/40 hover:border-emerald-500/25 hover:shadow-lg hover:shadow-emerald-500/5 bg-gradient-to-b from-card to-card/90 transition-all duration-300">
            <CardHeader className="relative pb-4 border-b border-border/20 bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-transparent">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <AtomIcon className="size-20 text-emerald-500" />
              </div>
              <CardTitle className="flex items-center text-sm font-bold tracking-wider text-foreground">
                <AtomIcon className="size-4 text-emerald-500 mr-2 animate-spin-slow" />
                {t.settings.models.categories.science}
              </CardTitle>
              <CardDescription className="text-xs leading-relaxed text-muted-foreground/90 max-w-xl">
                {t.settings.models.categories.scienceDesc}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2 pt-5">
              {renderKeyField(
                "MP_API_KEY", 
                t.settings.models.fields.mp, 
                <AtomIcon className="size-3.5 text-emerald-500/80" />
              )}
              {renderKeyField(
                "CITRINATION_API_KEY", 
                t.settings.models.fields.citrination, 
                <BeakerIcon className="size-3.5 text-teal-500/80" />
              )}
            </CardContent>
          </Card>

          {/* Card 2: Academic Literature Search */}
          <Card className="overflow-hidden border-border/40 hover:border-sky-500/25 hover:shadow-lg hover:shadow-sky-500/5 bg-gradient-to-b from-card to-card/90 transition-all duration-300">
            <CardHeader className="relative pb-4 border-b border-border/20 bg-gradient-to-r from-sky-500/10 via-indigo-500/5 to-transparent">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <BookOpenIcon className="size-20 text-sky-500" />
              </div>
              <CardTitle className="flex items-center text-sm font-bold tracking-wider text-foreground">
                <BookOpenIcon className="size-4 text-sky-500 mr-2" />
                {t.settings.models.categories.literature}
              </CardTitle>
              <CardDescription className="text-xs leading-relaxed text-muted-foreground/90 max-w-xl">
                {t.settings.models.categories.literatureDesc}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2 pt-5">
              {renderKeyField(
                "SEMANTIC_SCHOLAR_API_KEY", 
                t.settings.models.fields.semanticScholar, 
                <BookOpenIcon className="size-3.5 text-sky-500/80" />
              )}
              {renderKeyField(
                "NCBI_API_KEY", 
                t.settings.models.fields.ncbi, 
                <BookOpenIcon className="size-3.5 text-rose-500/80" />
              )}
            </CardContent>
          </Card>

          {/* Card 3: Core LLM Services */}
          <Card data-tour="llm-keys-card" className="overflow-hidden border-border/40 hover:border-purple-500/25 hover:shadow-lg hover:shadow-purple-500/5 bg-gradient-to-b from-card to-card/90 transition-all duration-300">
            <CardHeader className="relative pb-4 border-b border-border/20 bg-gradient-to-r from-purple-500/10 via-pink-500/5 to-transparent">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <CpuIcon className="size-20 text-purple-500" />
              </div>
              <CardTitle className="flex items-center text-sm font-bold tracking-wider text-foreground">
                <CpuIcon className="size-4 text-purple-500 mr-2" />
                {t.settings.models.categories.models}
              </CardTitle>
              <CardDescription className="text-xs leading-relaxed text-muted-foreground/90 max-w-xl">
                {t.settings.models.categories.modelsDesc}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2 pt-5">
              {renderKeyField(
                "DEEPSEEK_API_KEY", 
                t.settings.models.fields.deepseek, 
                <BinaryIcon className="size-3.5 text-sky-500/80" />
              )}
              {renderKeyField(
                "DASHSCOPE_API_KEY", 
                t.settings.models.fields.dashscope, 
                <ZapIcon className="size-3.5 text-cyan-500/80" />
              )}
              {renderKeyField(
                "GLM_API_KEY", 
                t.settings.models.fields.glm, 
                <SparklesIcon className="size-3.5 text-violet-500/80" />
              )}
              {renderKeyField(
                "ANTHROPIC_API_KEY", 
                t.settings.models.fields.anthropic, 
                <SparklesIcon className="size-3.5 text-amber-500/80" />
              )}
              {renderKeyField(
                "OPENAI_API_KEY", 
                t.settings.models.fields.openai, 
                <FingerprintIcon className="size-3.5 text-emerald-500/80" />
              )}
              {renderKeyField(
                "GEMINI_API_KEY", 
                t.settings.models.fields.gemini, 
                <SparklesIcon className="size-3.5 text-indigo-500/80" />
              )}
            </CardContent>
          </Card>

          {/* Card 4: Research Utilities & Tool Interfaces */}
          <Card className="overflow-hidden border-border/40 hover:border-amber-500/25 hover:shadow-lg hover:shadow-amber-500/5 bg-gradient-to-b from-card to-card/90 transition-all duration-300">
            <CardHeader className="relative pb-4 border-b border-border/20 bg-gradient-to-r from-amber-500/10 via-orange-500/5 to-transparent">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <WrenchIcon className="size-20 text-amber-500" />
              </div>
              <CardTitle className="flex items-center text-sm font-bold tracking-wider text-foreground">
                <WrenchIcon className="size-4 text-amber-500 mr-2" />
                {t.settings.models.categories.infra}
              </CardTitle>
              <CardDescription className="text-xs leading-relaxed text-muted-foreground/90 max-w-xl">
                {t.settings.models.categories.infraDesc}
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2 pt-5">
              {renderKeyField(
                "MINERU_API_TOKEN", 
                t.settings.models.fields.mineru, 
                <FileTextIcon className="size-3.5 text-indigo-500/80" />
              )}
              {renderKeyField(
                "GITHUB_TOKEN", 
                t.settings.models.fields.github, 
                <GithubIcon className="size-3.5 text-foreground/70" />
              )}
              {renderKeyField(
                "HF_TOKEN", 
                t.settings.models.fields.hf, 
                <GlobeIcon className="size-3.5 text-yellow-600/85" />
              )}
              {renderKeyField(
                "SERPER_API_KEY", 
                t.settings.models.fields.serper, 
                <SearchIcon className="size-3.5 text-sky-500/80" />
              )}
              {renderKeyField(
                "TAVILY_API_KEY", 
                t.settings.models.fields.tavily, 
                <SearchIcon className="size-3.5 text-blue-500/80" />
              )}
              {renderKeyField(
                "JINA_API_KEY", 
                t.settings.models.fields.jina, 
                <FileTextIcon className="size-3.5 text-emerald-500/80" />
              )}
            </CardContent>
          </Card>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border/10">
            <Button
              type="submit"
              disabled={saving}
              className="gap-2 px-5 py-2 text-sm font-bold tracking-wide shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/30 transition-all duration-300"
            >
              <SaveIcon className="size-4" />
              {saving ? t.settings.models.saving : t.settings.models.save}
            </Button>
          </div>
        </form>
      </SettingsSection>
    </div>
  );
}
