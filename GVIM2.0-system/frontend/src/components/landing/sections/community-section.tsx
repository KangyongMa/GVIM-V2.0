"use client";

import { GitHubLogoIcon } from "@radix-ui/react-icons";
import Link from "next/link";

import { AuroraText } from "@/components/ui/aurora-text";
import { Button } from "@/components/ui/button";

import { Section } from "../section";

export function CommunitySection() {
  return (
    <Section
      title={
        <AuroraText colors={["#60A5FA", "#A5FA60", "#A560FA"]}>
          加入开源社区
        </AuroraText>
      }
      subtitle="贡献您的卓越灵感，共同塑造 GVIM AI 的未来。在这里携手创新，赋能科学前沿探索。"
    >
      <div className="flex justify-center">
        <Button className="text-xl" size="lg" asChild>
          <Link
            href="https://github.com/bytedance/gvim"
            target="_blank"
            rel="noopener noreferrer"
          >
            <GitHubLogoIcon />
            立即参与贡献
          </Link>
        </Button>
      </div>
    </Section>
  );
}
