"use client";

import { useState, useEffect } from "react";
import { MagnifyingGlass, Plus, MapPin, Quotes, Image, Article, MapTrifold, CoffeeBean } from "@phosphor-icons/react";
import * as api from "@/lib/api";
import type { InspirationItem, InspirationCollection } from "@/types/inspirations";
import { InspirationCard } from "@/components/inspirations/InspirationCard";
import { InspirationFilters } from "@/components/inspirations/InspirationFilters";
import { InspirationStatsPanel } from "@/components/inspirations/InspirationStatsPanel";
import { CollectionList } from "@/components/inspirations/CollectionList";

export default function InspirationsPage() {
  const [inspirations, setInspirations] = useState<InspirationItem[]>([]);
  const [collections, setCollections] = useState<InspirationCollection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchKeyword, setSearchKeyword] = useState("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [showCreateCollection, setShowCreateCollection] = useState(false);

  useEffect(() => {
    loadInspirations();
    loadCollections();
  }, [selectedType, selectedCategory]);

  const loadInspirations = async () => {
    try {
      setLoading(true);
      const response = await api.getInspirations({
        keyword: searchKeyword || undefined,
        type: selectedType || undefined,
        category: selectedCategory || undefined,
      });
      setInspirations(response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadCollections = async () => {
    try {
      const response = await api.getInspirationCollections();
      setCollections(response.items || []);
    } catch (err) {
      console.error("加载分组失败:", err);
    }
  };

  const handleSearch = () => {
    loadInspirations();
  };

  const handleCreateCollection = async (name: string, description?: string) => {
    try {
      await api.createInspirationCollection({ name, description });
      await loadCollections();
      setShowCreateCollection(false);
    } catch (err) {
      console.error("创建分组失败:", err);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "poi":
      case "restaurant":
      case "activity":
        return MapPin;
      case "quote":
        return Quotes;
      case "photo":
        return Image;
      case "article":
        return Article;
      case "route":
      case "map":
        return MapTrifold;
      default:
        return CoffeeBean;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-ink mb-2">收藏灵感</h1>
        <p className="text-muted">把打动你的地点、句子与路线，先轻轻收下。</p>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <MagnifyingGlass className="absolute left-4 top-1/2 -translate-y-1/2 text-muted size-5" />
        <input
          type="text"
          placeholder="搜索地点、活动、句子或路线灵感..."
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
      <InspirationFilters
        selectedType={selectedType}
        selectedCategory={selectedCategory}
        onTypeChange={setSelectedType}
        onCategoryChange={setSelectedCategory}
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
      {!loading && inspirations.length === 0 && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-card-soft rounded-full mb-4">
            <CoffeeBean className="size-8 text-muted" />
          </div>
          <h3 className="text-xl font-semibold text-ink mb-2">还没有灵感</h3>
          <p className="text-muted mb-6">在浏览城市志或游笺时，收藏打动你的内容</p>
          <button
            onClick={() => (window.location.href = "/city-guide")}
            className="inline-flex items-center gap-2 px-6 py-3 bg-pine-green text-white rounded-xl hover:bg-pine-green/90 transition-colors"
          >
            <MapPin className="size-5" />
            探索城市志
          </button>
        </div>
      )}

      {/* Inspiration Grid */}
      {!loading && inspirations.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {inspirations.map((inspiration) => (
            <InspirationCard
              key={inspiration.id}
              inspiration={inspiration}
              Icon={getTypeIcon(inspiration.type)}
            />
          ))}
        </div>
      )}
    </div>
  );
}