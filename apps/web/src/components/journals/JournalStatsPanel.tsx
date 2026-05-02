"use client";

import { MapPin, Calendar, Clock, Star, TrendUp, Plus } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import * as api from "@/lib/api";

export function JournalStatsPanel() {
  const [stats, setStats] = useState({
    total: 0,
    thisMonth: 0,
    favoriteCount: 0,
    totalDuration: 0,
    totalDistance: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const response = await api.getJournals({ page: 1, page_size: 100 });
      const journals = response.items || [];

      const now = new Date();
      const thisMonthJournals = journals.filter((j) => {
        const journalDate = new Date(j.created_at);
        return (
          journalDate.getMonth() === now.getMonth() &&
          journalDate.getFullYear() === now.getFullYear()
        );
      });

      setStats({
        total: journals.length,
        thisMonth: thisMonthJournals.length,
        favoriteCount: journals.filter((j) => j.is_favorite).length,
        totalDuration: journals.reduce((sum, j) => sum + (j.total_duration_minutes || 0), 0),
        totalDistance: journals.reduce((sum, j) => sum + (j.total_distance_meters || 0), 0),
      });
    } catch (error) {
      console.error("加载统计数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    return hours > 0 ? `${hours}小时` : `${minutes}分钟`;
  };

  const formatDistance = (meters: number) => {
    return `${(meters / 1000).toFixed(1)}公里`;
  };

  return (
    <div className="space-y-6">
      {/* Quick Actions */}
      <div className="bg-card-bg rounded-2xl p-5 shadow-paper">
        <h3 className="text-lg font-semibold text-ink mb-4">快速开始</h3>
        <div className="space-y-2">
          <button
            onClick={() => (window.location.href = "/")}
            className="w-full flex items-center gap-3 px-4 py-3 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors"
          >
            <Plus className="size-5" />
            <span className="font-medium">创建新游笺</span>
          </button>
          <button
            onClick={() => (window.location.href = "/inspirations")}
            className="w-full flex items-center gap-3 px-4 py-3 bg-white border border-line text-ink rounded-xl hover:bg-card-soft transition-colors"
          >
            <Star className="size-5" />
            <span className="font-medium">收藏灵感</span>
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="bg-card-bg rounded-2xl p-5 shadow-paper">
        <h3 className="text-lg font-semibold text-ink mb-4">我的足迹</h3>

        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-12 bg-card-soft rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Total Journals */}
            <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
              <div className="p-2 bg-clay-orange/10 rounded-lg">
                <Calendar className="size-5 text-clay-orange" />
              </div>
              <div className="flex-1">
                <p className="text-2xl font-bold text-ink">{stats.total}</p>
                <p className="text-xs text-muted">总游笺</p>
              </div>
            </div>

            {/* This Month */}
            <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
              <div className="p-2 bg-pine-green/10 rounded-lg">
                <TrendUp className="size-5 text-pine-green" />
              </div>
              <div className="flex-1">
                <p className="text-2xl font-bold text-ink">{stats.thisMonth}</p>
                <p className="text-xs text-muted">本月新增</p>
              </div>
            </div>

            {/* Favorites */}
            <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
              <div className="p-2 bg-warning/10 rounded-lg">
                <Star className="size-5 text-warning" />
              </div>
              <div className="flex-1">
                <p className="text-2xl font-bold text-ink">{stats.favoriteCount}</p>
                <p className="text-xs text-muted">已收藏</p>
              </div>
            </div>

            {/* Total Duration */}
            <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
              <div className="p-2 bg-pine-green/10 rounded-lg">
                <Clock className="size-5 text-pine-green" />
              </div>
              <div className="flex-1">
                <p className="text-2xl font-bold text-ink">{formatDuration(stats.totalDuration)}</p>
                <p className="text-xs text-muted">总时长</p>
              </div>
            </div>

            {/* Total Distance */}
            <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
              <div className="p-2 bg-pine-green/10 rounded-lg">
                <MapPin className="size-5 text-pine-green" />
              </div>
              <div className="flex-1">
                <p className="text-2xl font-bold text-ink">{formatDistance(stats.totalDistance)}</p>
                <p className="text-xs text-muted">总距离</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="bg-gradient-to-br from-pine-green-soft to-white rounded-2xl p-5 shadow-paper">
        <h3 className="text-sm font-semibold text-pine-green mb-2">小贴士</h3>
        <p className="text-xs text-muted leading-relaxed">
          在"今日足迹"页面结束行程后，可以保存为游笺，方便日后回忆和复用路线。
        </p>
      </div>
    </div>
  );
}