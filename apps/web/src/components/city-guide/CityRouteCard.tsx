"use client";

import { Clock, MapPin, Signpost, ArrowRight } from "@phosphor-icons/react";
import type { CityRoute } from "@/types/city-guide";

interface CityRouteCardProps {
  route: CityRoute;
}

export function CityRouteCard({ route }: CityRouteCardProps) {
  const getRouteTypeColor = (type: string) => {
    switch (type) {
      case "city_walk":
        return "bg-pine-green/10 text-pine-green";
      case "family":
        return "bg-blue-100 text-blue-700";
      case "cafe":
        return "bg-amber-100 text-amber-700";
      case "museum":
        return "bg-purple-100 text-purple-700";
      case "rainy_day":
        return "bg-gray-100 text-gray-700";
      case "weekend":
        return "bg-clay-orange/10 text-clay-orange";
      default:
        return "bg-card-soft text-muted";
    }
  };

  const getRouteTypeText = (type: string) => {
    const map: Record<string, string> = {
      city_walk: "City Walk",
      family: "亲子",
      cafe: "咖啡",
      museum: "博物馆",
      rainy_day: "雨天",
      weekend: "周末",
    };
    return map[type] || type;
  };

  return (
    <div className="bg-card-bg rounded-2xl overflow-hidden shadow-paper hover:shadow-paper-hover transition-all duration-300 group">
      {/* Cover Image */}
      <div className="relative h-48 bg-card-soft overflow-hidden">
        {route.cover_image_url ? (
          <img
            src={route.cover_image_url}
            alt={route.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-pine-green/20 to-clay-orange/20">
            <Signpost className="size-12 text-muted/30" />
          </div>
        )}

        {/* Route Type Badge */}
        <div className="absolute top-3 left-3">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRouteTypeColor(route.route_type)}`}>
            {getRouteTypeText(route.route_type)}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="text-lg font-semibold text-ink mb-2 line-clamp-2 group-hover:text-clay-orange transition-colors">
          {route.title}
        </h3>

        <p className="text-sm text-ink/70 mb-4 line-clamp-2">{route.description}</p>

        {/* Stats */}
        <div className="flex items-center gap-4 text-sm text-muted mb-4">
          <div className="flex items-center gap-1">
            <Clock className="size-4" />
            <span>{Math.round(route.duration_minutes / 60)}小时</span>
          </div>
          <div className="flex items-center gap-1">
            <MapPin className="size-4" />
            <span>{route.distance_km.toFixed(1)}km</span>
          </div>
          <div className="flex items-center gap-1">
            <Signpost className="size-4" />
            <span>{route.stops.length}站</span>
          </div>
        </div>

        {/* Tags */}
        {route.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {route.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-pine-green/10 text-pine-green text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
            {route.tags.length > 3 && (
              <span className="px-2 py-1 bg-card-soft text-muted text-xs rounded-full">
                +{route.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Action */}
        <button
          onClick={() => {
            const query = `周末下午想走「${route.title}」这条路线，大约${Math.round(route.duration_minutes / 60)}小时`;
            window.location.href = `/?query=${encodeURIComponent(query)}`;
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors font-medium"
        >
          生成这条路线
          <ArrowRight className="size-4" />
        </button>
      </div>
    </div>
  );
}