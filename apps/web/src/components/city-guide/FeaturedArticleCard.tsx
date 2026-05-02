"use client";

import { Star, ArrowRight } from "@phosphor-icons/react";
import type { CityArticle } from "@/types/city-guide";

interface FeaturedArticleCardProps {
  article: CityArticle;
  onAction: (articleId: string, action: "save" | "plan") => void;
}

export function FeaturedArticleCard({ article, onAction }: FeaturedArticleCardProps) {
  return (
    <div className="bg-card-bg rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-hover transition-all duration-300">
      <div className="flex flex-col md:flex-row">
        {/* Image */}
        <div className="md:w-2/5 relative h-64 md:h-auto">
          {article.cover_image_url ? (
            <img
              src={article.cover_image_url}
              alt={article.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-pine-green/20 to-clay-orange/20" />
          )}
        </div>

        {/* Content */}
        <div className="md:w-3/5 p-6">
          <div className="flex items-center gap-2 mb-3">
            <span className="px-3 py-1 bg-clay-orange/10 text-clay-orange rounded-full text-xs font-medium">
              精选专题
            </span>
            <span className="text-sm text-muted">{article.reading_minutes} 分钟阅读</span>
          </div>

          <h3 className="text-2xl font-bold text-ink mb-3">{article.title}</h3>

          {article.subtitle && (
            <p className="text-base text-muted mb-4">{article.subtitle}</p>
          )}

          <p className="text-sm text-ink/70 mb-6 line-clamp-3">{article.excerpt}</p>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onAction(article.id, "plan")}
              className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors font-medium"
            >
              生成路线
              <ArrowRight className="size-5" />
            </button>
            <button
              onClick={() => onAction(article.id, "save")}
              className="px-5 py-2.5 bg-white border border-line text-ink rounded-xl hover:bg-card-soft transition-colors font-medium flex items-center gap-2"
            >
              <Star className="size-5" />
              加入灵感
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}