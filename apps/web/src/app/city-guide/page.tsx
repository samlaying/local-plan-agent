"use client";

import { useState, useEffect } from "react";
import { Newspaper, MapPin, Calendar, Star, ArrowRight, BookOpen } from "@phosphor-icons/react";
import * as api from "@/lib/api";
import type { CityArticle, CityRoute, CityEvent } from "@/types/city-guide";
import { CityGuideHero } from "@/components/city-guide/CityGuideHero";
import { CityGuideTabs } from "@/components/city-guide/CityGuideTabs";
import { FeaturedArticleCard } from "@/components/city-guide/FeaturedArticleCard";
import { CityArticleCard } from "@/components/city-guide/CityArticleCard";
import { CityRouteCard } from "@/components/city-guide/CityRouteCard";
import { CityEventList } from "@/components/city-guide/CityEventList";
import { EditorPicks } from "@/components/city-guide/EditorPicks";

export default function CityGuidePage() {
  const [data, setData] = useState<{
    featured_article?: CityArticle | null;
    weekly_topic?: any | null;
    articles: CityArticle[];
    routes: CityRoute[];
    events: CityEvent[];
    editor_picks: CityArticle[];
  }>({
    articles: [],
    routes: [],
    events: [],
    editor_picks: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  useEffect(() => {
    loadCityGuide();
  }, [selectedCategory]);

  const loadCityGuide = async () => {
    try {
      setLoading(true);
      const response = await api.getCityGuideHome({});
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const handleArticleAction = async (articleId: string, action: "save" | "plan") => {
    if (action === "save") {
      try {
        await api.saveArticleToInspirations(articleId);
        alert("已加入灵感");
      } catch (err) {
        console.error("加入灵感失败:", err);
      }
    } else if (action === "plan") {
      // 跳转到规划页面并填充 query
      const article = data.articles.find((a) => a.id === articleId);
      if (article) {
        const query = `周末下午想参考「${article.title}」安排一条半日路线，别太累。`;
        window.location.href = `/?query=${encodeURIComponent(query)}`;
      }
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-ink mb-2">城市志</h1>
        <p className="text-muted">像读一本本地生活杂志一样，发现这座城的细节与气味。</p>
      </div>

      {/* Hero Section */}
      <CityGuideHero
        featuredArticle={data.featured_article}
        weeklyTopic={data.weekly_topic}
        onArticleClick={handleArticleAction}
      />

      {/* Category Tabs */}
      <div>
        <CityGuideTabs
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
        />
      </div>

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-card-bg rounded-2xl p-6 animate-pulse">
              <div className="h-40 bg-card-soft rounded-xl mb-4" />
              <div className="h-6 bg-card-soft rounded mb-2" />
              <div className="h-4 bg-card-soft rounded w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-danger/10 border border-danger text-danger px-6 py-4 rounded-xl">
          {error}
        </div>
      )}

      {/* Content Sections */}
      {!loading && (
        <div className="space-y-12">
          {/* Featured Article */}
          {data.featured_article && (
            <FeaturedArticleCard
              article={data.featured_article}
              onAction={handleArticleAction}
            />
          )}

          {/* Articles Grid */}
          {data.articles.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-ink flex items-center gap-2">
                  <Newspaper className="size-6 text-clay-orange" />
                  城市专题
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {data.articles.map((article) => (
                  <CityArticleCard
                    key={article.id}
                    article={article}
                    onAction={handleArticleAction}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Routes Grid */}
          {data.routes.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-ink flex items-center gap-2">
                  <MapPin className="size-6 text-pine-green" />
                  街区路线
                </h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {data.routes.map((route) => (
                  <CityRouteCard key={route.id} route={route} />
                ))}
              </div>
            </section>
          )}

          {/* Events List */}
          {data.events.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-ink flex items-center gap-2">
                  <Calendar className="size-6 text-clay-orange" />
                  城市日历
                </h2>
              </div>
              <CityEventList events={data.events} />
            </section>
          )}

          {/* Editor Picks */}
          {data.editor_picks.length > 0 && (
            <EditorPicks
              articles={data.editor_picks}
              onAction={handleArticleAction}
            />
          )}
        </div>
      )}
    </div>
  );
}