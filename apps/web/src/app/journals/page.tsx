"use client";

import { useState, useEffect } from "react";
import { MagnifyingGlass, Plus, Calendar, Clock, MapPin, Users, Star, Archive } from "@phosphor-icons/react";
import * as api from "@/lib/api";
import type { TravelJournal, TravelJournalStatus, TravelJournalScene } from "@/types/journals";
import { JournalCard } from "@/components/journals/JournalCard";
import { JournalFilters } from "@/components/journals/JournalFilters";
import { JournalStatsPanel } from "@/components/journals/JournalStatsPanel";

export default function JournalsPage() {
  const [journals, setJournals] = useState<TravelJournal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [selectedScene, setSelectedScene] = useState<string | undefined>();
  const [sortBy, setSortBy] = useState<string>("recent");

  useEffect(() => {
    loadJournals();
  }, [selectedStatus, selectedScene, sortBy]);

  const loadJournals = async () => {
    try {
      setLoading(true);
      const response = await api.getJournals({
        keyword: searchKeyword || undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        scene: selectedScene,
        sort: sortBy,
      });
      setJournals(response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadJournals();
  };

  const handleToggleFavorite = async (journalId: string, isFavorite: boolean) => {
    try {
      await api.updateJournal(journalId, { is_favorite: !isFavorite });
      await loadJournals();
    } catch (err) {
      console.error("切换收藏状态失败:", err);
    }
  };

  const handleArchive = async (journalId: string) => {
    if (!confirm("确定要归档这个游笺吗？")) return;

    try {
      await api.archiveJournal(journalId);
      await loadJournals();
    } catch (err) {
      console.error("归档失败:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-ink mb-2">我的游笺</h1>
        <p className="text-muted">把走过的半日时光，收进自己的城市手账。</p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <MagnifyingGlass className="absolute left-4 top-1/2 -translate-y-1/2 text-muted size-5" />
        <input
          type="text"
          placeholder="搜索游笺标题、地点、心情..."
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="w-full pl-12 pr-4 py-3 bg-white border border-line rounded-xl text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-clay-orange focus:border-transparent"
        />
        <button
          onClick={handleSearch}
          className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-1.5 bg-clay-orange text-white rounded-lg hover:bg-clay-orange-dark transition-colors"
        >
          搜索
        </button>
      </div>

      {/* Filters */}
      <JournalFilters
        selectedStatus={selectedStatus}
        selectedScene={selectedScene}
        sortBy={sortBy}
        onStatusChange={setSelectedStatus}
        onSceneChange={setSelectedScene}
        onSortChange={setSortBy}
      />

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

      {/* Empty State */}
      {!loading && journals.length === 0 && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-card-soft rounded-full mb-4">
            <Calendar className="size-8 text-muted" />
          </div>
          <h3 className="text-xl font-semibold text-ink mb-2">还没有游笺</h3>
          <p className="text-muted mb-6">开始你的第一次半日游，记录美好时光</p>
          <button
            onClick={() => window.location.href = "/"}
            className="inline-flex items-center gap-2 px-6 py-3 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors"
          >
            <Plus className="size-5" />
            创建新游笺
          </button>
        </div>
      )}

      {/* Journal Grid */}
      {!loading && journals.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {journals.map((journal) => (
            <JournalCard
              key={journal.id}
              journal={journal}
              onToggleFavorite={() => handleToggleFavorite(journal.id, journal.is_favorite)}
              onArchive={() => handleArchive(journal.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}