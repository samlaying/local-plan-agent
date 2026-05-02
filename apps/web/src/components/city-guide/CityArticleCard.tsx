"use client";

import { Clock, Star, ArrowRight, MapPin } from "@phosphor-icons/react";
import type { CityArticle } from "@/types/city-guide";

interface CityArticleCardProps {
  article: CityArticle;
  onAction: (articleId: string, action: "save" | "plan") => void;
}

export function CityArticleCard({ article, onAction }: CityArticleCardProps) {
  const getCategoryColor = (category: string) => {
    switch (category) {
      case "weekly_feature":
        return "bg-clay-orange/10 text-clay-orange";
      case "neighborhood_walk":
        return "bg-pine-green/10 text-pine-green";
      case "cafe_bookstore":
        return "bg-amber-100 text-amber-700";
      case "museum_exhibition":
        return "bg-purple-100 text-purple-700";
      case "family_day":
        return "bg-blue-100 text-blue-700";
      case "rainy_day":
        return "bg-gray-100 text-gray-700";
      default:
        return "bg-card-soft text-muted";
    }
  };

  const getCategoryText = (category: string) => {
    const map: Record<string, string> = {
      weekly_feature: "本周策展",
      neighborhood_walk: "街区漫游",
      cafe_bookstore: "咖啡与书店",
      museum_exhibition: "展览与博物馆",
      family_day: "亲子目的地",
      rainy_day: "雨天备选",
      city_calendar: "城市日历",
    };
    return map[category] || category;
  };

  return (
    <div className="bg-card-bg rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-hover transition-all duration-300 group">
      {/* Cover Image */}
      <div className="relative h-48 bg-card-soft overflow-hidden">
        {article.cover_image_url ? (
          <img
            src={article.cover_image_url}
            alt={article.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-pine-green/20 to-clay-orange/20">
            <div className="text-center">
              <MapPin className="size-12 text-muted/30 mx-auto mb-2" />
              <p className="text-sm text-muted/50">{article.city}</p>
            </div>
          </div>
        )}

        {/* Category Badge */}
        <div className="absolute top-3 left-3">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getCategoryColor(article.category)}`}>
            {getCategoryText(article.category)}
          </span>
        </div>

        {/* Reading Time */}
        <div className="absolute top-3 right-3">
          <span className="px-3 py-1 bg-white/90 backdrop-blur rounded-full text-xs font-medium text-ink flex items-center gap-1">
            <Clock className="size-3" />
            {article.reading_minutes} 分钟
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="text-lg font-semibold text-ink mb-2 line-clamp-2 group-hover:text-clay-orange transition-colors">
          {article.title}
        </h3>

        {article.subtitle && (
          <p className="text-sm text-muted mb-3 line-clamp-1">{article.subtitle}</p>
        )}

        <p className="text-sm text-ink/70 mb-4 line-clamp-3">{article.excerpt}</p>

        {/* Tags */}
        {article.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {article.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-pine-green/10 text-pine-green text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
            {article.tags.length > 3 && (
              <span className="px-2 py-1 bg-card-soft text-muted text-xs rounded-full">
                +{article.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onAction(article.id, "plan")}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-clay-orange text-white rounded-lg hover:bg-clay-orange-dark transition-colors text-sm font-medium"
          >
            生成路线
            <ArrowRight className="size-4" />
          </button>
          <button
            onClick={() => onAction(article.id, "save")}
            className="p-2 text-muted hover:text-warning hover:bg-warning/10 rounded-lg transition-colors"
            title="加入灵感"
          >
            <Star className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}