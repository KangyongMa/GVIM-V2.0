import Link from "next/link";

import { Card } from "@/components/ui/card";
import { pathOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

import { Section } from "../section";

export function CaseStudySection({ className }: { className?: string }) {
  const caseStudies = [
    {
      threadId: "7cfa5f8f-a2f8-47ad-acbd-da7137baf990",
      title: "NMR 图谱预测与未知结构解析",
      description:
        "自动化运行一维/二维 NMR 预测，并与实验光谱对比，快速确证未知有机分子结构。",
    },
    {
      threadId: "4f3e55ee-f853-43db-bfb3-7d1a411f03cb",
      title: "Pymatgen 晶体材料高通量设计",
      description:
        "从文献 PDF 中提取 DFT 计算参数，生成定制晶胞构型，并预测新材料的物理化学性质。",
    },
    {
      threadId: "21cfea46-34bd-4aa6-9e1f-3009452fbeb9",
      title: "ADME 与 pKa 特性虚拟评估",
      description:
        "对小分子候选药物进行高通量虚拟筛选，自动化预测其吸收、代谢特征及 pKa 常数。",
    },
    {
      threadId: "ad76c455-5bf9-4335-8517-fc03834ab828",
      title: "Opentrons 实验室机器人统筹",
      description:
        "自动生成并验证 Opentrons OT-2 API 脚本，零代码实现复杂的自动化移液与液体处理实验。",
    },
    {
      threadId: "d3e5adaf-084c-4dd5-9d29-94f1d6bccd98",
      title: "XRD 与光学能谱全栈模拟",
      description:
        "全栈模拟 XRD、红外 (IR)、质谱 (MS) 及 UV-Vis 光谱，以全面表征新设计的分子与晶体结构。",
    },
    {
      threadId: "3823e443-4e2b-4679-b496-a9506eae462b",
      title: "聚合与催化文献数据深度挖掘",
      description:
        "批量扫描数百篇聚合物与催化剂文献，自动化精准提取关键反应条件、催化剂结构与产率数据表。",
    },
  ];
  return (
    <Section
      className={className}
      title="真实科研案例展示"
      subtitle="查看 GVIM AI 如何在真实的化学与材料学前沿探索中提供核心生产力"
    >
      <div className="container-md mt-8 grid grid-cols-1 gap-4 px-4 md:grid-cols-2 md:px-20 lg:grid-cols-3">
        {caseStudies.map((caseStudy) => (
          <Link
            key={caseStudy.title}
            href={pathOfThread(caseStudy.threadId) + "?mock=true"}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Card className="group/card relative h-64 overflow-hidden">
              <div
                className="absolute inset-0 z-0 bg-cover bg-center bg-no-repeat transition-all duration-300 group-hover/card:scale-110 group-hover/card:brightness-90"
                style={{
                  backgroundImage: `url(/images/${caseStudy.threadId}.png)`,
                }}
              ></div>
              <div
                className={cn(
                  "flex h-full w-full translate-y-[calc(100%-60px)] flex-col items-center",
                  "transition-all duration-300",
                  "group-hover/card:translate-y-[calc(100%-128px)]",
                )}
              >
                <div
                  className="flex w-full flex-col p-4"
                  style={{
                    background:
                      "linear-gradient(to bottom, rgba(0, 0, 0, 0) 0%, rgba(0, 0, 0, 1) 100%)",
                  }}
                >
                  <div className="flex flex-col gap-2">
                    <h3 className="flex h-14 items-center text-xl font-bold text-shadow-black">
                      {caseStudy.title}
                    </h3>
                    <p className="box-shadow-black overflow-hidden text-sm text-white/85 text-shadow-black">
                      {caseStudy.description}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </Section>
  );
}
