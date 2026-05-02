"use client";

import { Lightbulb, MapPin, BookOpen, Plus } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import * as api from "@/lib/api";

export function InspirationStatsPanel() {
  const [stats, setStats] = useState({
    total: 0,
    collections: 0,
    visitedPlaces: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await api.getInspirations({ page_size: 1 });
      setStats({
        total: response.stats?.total || 0,
        collections: response.stats?.collections || 0,
        visitedPlaces: response.stats?.visited_places || 0,
      });
    } catch (error) {
      console.error("加载统计数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mb-6 bg-card-bg rounded-2xl p-5 shadow-paper">
      <h3 className="text-lg font-semibold text-ink mb-4">灵感统计</h3>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-card-soft rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Total Inspirations */}
          <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
            <div className="p-2 bg-clay-orange/10 rounded-lg">
              <Lightbulb className="size-5 text-clay-orange" />
            </div>
            <div className="flex-1">
              <p className="text-2xl font-bold text-ink">{stats.total}</p>
              <p className="text-xs text-muted">总灵感</p>
            </div>
          </div>

          {/* Collections */}
          <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
            <div className="p-2 bg-pine-green/10 rounded-lg">
              <BookOpen className="size-5 text-pine-green" />
            </div>
            <div className="flex-1">
              <p className="text-2xl font-bold text-ink">{stats.collections}</p>
              <p className="text-xs text-muted">灵感分组</p>
            </div>
          </div>

          {/* Visited Places */}
          <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
            <div className="p-2 bg-pine-green/10 rounded-lg">
              <MapPin className="size-5 text-pine-green" />
            </div>
            <div className="flex-1">
              <p className="text-2xl font-bold text-ink">{stats.visitedPlaces}</p>
              <p className="text-xs text-muted">已去过</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Add Button */}
      <button
        onClick={() => (window.location.href = "/city-guide")}
        className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-3 bg-white border border-line text-ink rounded-xl hover:bg-card-soft transition-colors text-sm font-medium"
      >
        <Plus className="size-4" />
        探索更多灵感
      </button>
    </div>
  );
}