"use client";

import { Star, ArrowRight } from "@phosphor-icons/react";
import type { CityArticle } from "@/types/city-guide";

interface CityGuideHeroProps {
  featuredArticle?: CityArticle | null;
  weeklyTopic?: any | null;
  onArticleClick: (articleId: string, action: "save" | "plan") => void;
}

export function CityGuideHero({ featuredArticle, weeklyTopic, onArticleClick }: CityGuideHeroProps) {
  if (!featuredArticle) return null;

  return (
    <div className="relative rounded-3xl overflow-hidden shadow-paper mb-8">
      {/* Background Image */}
      <div className="relative h-[400px] bg-gradient-to-br from-pine-green/20 to-clay-orange/20">
        {featuredArticle.cover_image_url && (
          <img
            src={featuredArticle.cover_image_url}
            alt={featuredArticle.title}
            className="w-full h-full object-cover"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-ink/40 to-transparent" />
      </div>

      {/* Content */}
      <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
        <div className="flex items-center gap-2 mb-3">
          <span className="px-3 py-1 bg-clay-orange rounded-full text-sm font-medium">
            本周策展
          </span>
          <span className="px-3 py-1 bg-white/20 backdrop-blur rounded-full text-sm">
            {featuredArticle.reading_minutes} 分钟阅读
          </span>
        </div>

        <h2 className="text-4xl font-bold mb-3">{featuredArticle.title}</h2>

        {featuredArticle.subtitle && (
          <p className="text-xl text-white/90 mb-4">{featuredArticle.subtitle}</p>
        )}

        <p className="text-lg text-white/80 mb-6 line-clamp-2 max-w-3xl">
          {featuredArticle.excerpt}
        </p>

        <div className="flex items-center gap-4">
          <button
            onClick={() => onArticleClick(featuredArticle.id, "plan")}
            className="inline-flex items-center gap-2 px-6 py-3 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors font-medium"
          >
            生成相关路线
            <ArrowRight className="size-5" />
          </button>
          <button
            onClick={() => onArticleClick(featuredArticle.id, "save")}
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/20 backdrop-blur text-white rounded-xl hover:bg-white/30 transition-colors font-medium"
          >
            <Star className="size-5" />
            加入灵感
          </button>
        </div>
      </div>
    </div>
  );
}