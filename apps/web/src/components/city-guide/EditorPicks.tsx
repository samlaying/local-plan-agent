"use client";

import { Sparkle, Star, ArrowRight } from "@phosphor-icons/react";
import type { CityArticle } from "@/types/city-guide";

interface EditorPicksProps {
  articles: CityArticle[];
  onAction: (articleId: string, action: "save" | "plan") => void;
}

export function EditorPicks({ articles, onAction }: EditorPicksProps) {
  if (articles.length === 0) return null;

  return (
    <section className="bg-gradient-to-br from-pine-green-soft to-white rounded-2xl p-6 shadow-paper">
      <div className="flex items-center gap-2 mb-6">
        <Sparkle className="size-6 text-pine-green" />
        <h2 className="text-2xl font-bold text-ink">编辑精选</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {articles.slice(0, 4).map((article) => (
          <div
            key={article.id}
            className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-300"
          >
            <div className="flex flex-col sm:flex-row">
              {/* Image */}
              <div className="sm:w-2/5 h-32 sm:h-auto relative">
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
              <div className="sm:w-3/5 p-4">
                <h3 className="text-base font-semibold text-ink mb-2 line-clamp-2">
                  {article.title}
                </h3>

                <p className="text-xs text-muted mb-3 line-clamp-2">{article.excerpt}</p>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onAction(article.id, "plan")}
                    className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-clay-orange text-white rounded-lg hover:bg-clay-orange-dark transition-colors text-xs font-medium"
                  >
                    生成路线
                    <ArrowRight className="size-3" />
                  </button>
                  <button
                    onClick={() => onAction(article.id, "save")}
                    className="p-1.5 text-muted hover:text-warning hover:bg-warning/10 rounded-lg transition-colors"
                    title="加入灵感"
                  >
                    <Star className="size-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}