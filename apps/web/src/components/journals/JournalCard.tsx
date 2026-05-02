"use client";

import Link from "next/link";
import { Calendar, Clock, MapPin, Users, Star, Archive, MapTrifold } from "@phosphor-icons/react";
import type { TravelJournal } from "@/types/journals";

interface JournalCardProps {
  journal: TravelJournal;
  onToggleFavorite: () => void;
  onArchive: () => void;
}

export function JournalCard({ journal, onToggleFavorite, onArchive }: JournalCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  };

  const formatDuration = (minutes?: number | null) => {
    if (!minutes) return "-";
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}.${Math.round((mins / 60) * 10)}小时` : `${mins}分钟`;
  };

  const formatDistance = (meters?: number | null) => {
    if (!meters) return "-";
    return `${(meters / 1000).toFixed(1)}km`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-success/10 text-success";
      case "ongoing":
        return "bg-clay-orange/10 text-clay-orange";
      case "planned":
        return "bg-pine-green/10 text-pine-green";
      default:
        return "bg-muted/10 text-muted";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "已完成";
      case "ongoing":
        return "进行中";
      case "planned":
        return "已计划";
      case "draft":
        return "草稿";
      default:
        return "已归档";
    }
  };

  return (
    <div className="bg-card-bg rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-hover transition-all duration-300 group">
      {/* Cover Image */}
      <Link href={`/journals/${journal.id}`}>
        <div className="relative h-40 bg-card-soft overflow-hidden">
          {journal.cover_image_url ? (
            <img
              src={journal.cover_image_url}
              alt={journal.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <MapTrifold className="size-12 text-muted/30" />
            </div>
          )}

          {/* Status Badge */}
          <div className="absolute top-3 left-3">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(journal.status)}`}>
              {getStatusText(journal.status)}
            </span>
          </div>

          {/* Favorite Button */}
          <button
            onClick={(e) => {
              e.preventDefault();
              onToggleFavorite();
            }}
            className="absolute top-3 right-3 p-2 rounded-full bg-white/90 hover:bg-white transition-colors"
          >
            <Star
              className={`size-5 ${journal.is_favorite ? "fill-warning text-warning" : "text-muted"}`}
              weight={journal.is_favorite ? "fill" : "regular"}
            />
          </button>
        </div>
      </Link>

      {/* Content */}
      <div className="p-5">
        <Link href={`/journals/${journal.id}`}>
          <h3 className="text-lg font-semibold text-ink mb-1 line-clamp-2 group-hover:text-clay-orange transition-colors">
            {journal.title}
          </h3>
        </Link>

        {journal.subtitle && (
          <p className="text-sm text-muted mb-3 line-clamp-1">{journal.subtitle}</p>
        )}

        {/* Date & Time */}
        <div className="flex items-center gap-4 text-sm text-muted mb-3">
          <div className="flex items-center gap-1">
            <Calendar className="size-4" />
            <span>{formatDate(journal.created_at)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="size-4" />
            <span>{formatDuration(journal.total_duration_minutes)}</span>
          </div>
        </div>

        {/* Location & Distance */}
        <div className="flex items-center gap-4 text-sm text-muted mb-3">
          <div className="flex items-center gap-1">
            <MapPin className="size-4" />
            <span className="line-clamp-1">{journal.city}</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-muted/60">·</span>
            <span>{formatDistance(journal.total_distance_meters)}</span>
          </div>
        </div>

        {/* Tags */}
        {journal.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {journal.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-pine-green-10 text-pine-green text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
            {journal.tags.length > 3 && (
              <span className="px-2 py-1 bg-card-soft text-muted text-xs rounded-full">
                +{journal.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-line">
          <div className="flex items-center gap-1 text-sm text-muted">
            <Users className="size-4" />
            <span>{journal.stop_count} 站</span>
          </div>

          {journal.status !== "archived" && (
            <button
              onClick={(e) => {
                e.preventDefault();
                onArchive();
              }}
              className="p-2 text-muted hover:text-danger hover:bg-danger/10 rounded-lg transition-colors"
              title="归档"
            >
              <Archive className="size-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}