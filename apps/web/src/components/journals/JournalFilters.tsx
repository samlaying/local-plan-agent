"use client";

import { Funnel, SortAscending } from "@phosphor-icons/react";

interface JournalFiltersProps {
  selectedStatus: string;
  selectedScene?: string;
  sortBy: string;
  onStatusChange: (status: string) => void;
  onSceneChange: (scene?: string) => void;
  onSortChange: (sort: string) => void;
}

export function JournalFilters({
  selectedStatus,
  selectedScene,
  sortBy,
  onStatusChange,
  onSceneChange,
  onSortChange,
}: JournalFiltersProps) {
  const statuses = [
    { value: "all", label: "全部" },
    { value: "completed", label: "已完成" },
    { value: "ongoing", label: "进行中" },
    { value: "favorite", label: "已收藏" },
  ];

  const scenes = [
    { value: "family", label: "亲子" },
    { value: "friends", label: "朋友" },
    { value: "couple", label: "情侣" },
    { value: "solo", label: "独行" },
  ];

  const sortOptions = [
    { value: "recent", label: "最近更新" },
    { value: "duration", label: "时长" },
    { value: "distance", label: "距离" },
  ];

  return (
    <div className="mb-6 space-y-4">
      {/* Status Filters */}
      <div className="flex flex-wrap gap-2">
        {statuses.map((status) => (
          <button
            key={status.value}
            onClick={() => onStatusChange(status.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedStatus === status.value
                ? "bg-clay-orange text-white"
                : "bg-white text-muted hover:bg-card-soft"
            }`}
          >
            {status.label}
          </button>
        ))}
      </div>

      {/* Scene & Sort Filters */}
      <div className="flex items-center gap-4">
        {/* Scene Filter */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted">场景:</span>
          <div className="flex gap-1">
            <button
              onClick={() => onSceneChange(undefined)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                !selectedScene
                  ? "bg-pine-green text-white"
                  : "bg-white text-muted hover:bg-card-soft"
              }`}
            >
              全部
            </button>
            {scenes.map((scene) => (
              <button
                key={scene.value}
                onClick={() => onSceneChange(scene.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  selectedScene === scene.value
                    ? "bg-pine-green text-white"
                    : "bg-white text-muted hover:bg-card-soft"
                }`}
              >
                {scene.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sort Options */}
        <div className="flex items-center gap-2 ml-auto">
          <SortAscending className="size-4 text-muted" />
          <select
            value={sortBy}
            onChange={(e) => onSortChange(e.target.value)}
            className="px-3 py-1.5 bg-white border border-line rounded-lg text-sm text-ink focus:outline-none focus:ring-2 focus:ring-clay-orange"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
