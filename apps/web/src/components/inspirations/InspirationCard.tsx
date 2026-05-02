"use client";

import { MapPin, Star, Plus, ArrowRight } from "@phosphor-icons/react";
import type { InspirationItem } from "@/types/inspirations";
import * as api from "@/lib/api";

interface InspirationCardProps {
  inspiration: InspirationItem;
  Icon: any;
}

export function InspirationCard({ inspiration, Icon }: InspirationCardProps) {
  const handleAddToPlanning = () => {
    // TODO: 后续接入规划功能
    alert("加入规划草案功能即将上线");
  };

  const getCardStyle = (type: string) => {
    switch (type) {
      case "poi":
      case "photo":
      case "article":
        return "image-card";
      case "quote":
      case "note":
        return "paper-card";
      case "route":
      case "map":
        return "map-card";
      default:
        return "default-card";
    }
  };

  return (
    <div className={`bg-card-bg rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-hover transition-all duration-300 group ${getCardStyle(inspiration.type)}`}>
      {/* Cover Image / Visual */}
      {inspiration.cover_image_url ? (
        <div className="relative h-40 bg-card-soft overflow-hidden">
          <img
            src={inspiration.cover_image_url}
            alt={inspiration.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
          <div className="absolute top-3 left-3">
            <div className="p-2 bg-white/90 rounded-lg">
              <Icon className="size-5 text-clay-orange" />
            </div>
          </div>
        </div>
      ) : (
        <div className="relative h-40 bg-gradient-to-br from-pine-green-soft to-card-soft flex items-center justify-center">
          <Icon className="size-12 text-muted/30" />
        </div>
      )}

      {/* Content */}
      <div className="p-5">
        <h3 className="text-lg font-semibold text-ink mb-2 line-clamp-2 group-hover:text-clay-orange transition-colors">
          {inspiration.title}
        </h3>

        {inspiration.description && (
          <p className="text-sm text-muted mb-3 line-clamp-2">{inspiration.description}</p>
        )}

        {inspiration.content && (
          <p className="text-sm text-ink/80 mb-3 line-clamp-3 italic border-l-2 border-clay-orange pl-3">
            {inspiration.content}
          </p>
        )}

        {/* Location Info */}
        {inspiration.location && (
          <div className="flex items-center gap-1 text-sm text-muted mb-3">
            <MapPin className="size-4" />
            <span className="line-clamp-1">
              {inspiration.location.address || `${inspiration.city}${inspiration.district ? " · " + inspiration.district : ""}`}
            </span>
          </div>
        )}

        {/* Tags */}
        {inspiration.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {inspiration.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-pine-green/10 text-pine-green text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
            {inspiration.tags.length > 3 && (
              <span className="px-2 py-1 bg-card-soft text-muted text-xs rounded-full">
                +{inspiration.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleAddToPlanning}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-clay-orange text-white rounded-lg hover:bg-clay-orange-dark transition-colors text-sm font-medium"
          >
            <Plus className="size-4" />
            加入规划
          </button>
          <button
            className="p-2 text-muted hover:text-clay-orange hover:bg-clay-orange/10 rounded-lg transition-colors"
            title="收藏"
          >
            <Star className="size-4" />
          </button>
        </div>

        {/* Source Badge */}
        <div className="mt-3 pt-3 border-t border-line">
          <span className="text-xs text-muted">
            来源: {inspiration.source === "manual" ? "手动添加" : inspiration.source}
          </span>
        </div>
      </div>
    </div>
  );
}