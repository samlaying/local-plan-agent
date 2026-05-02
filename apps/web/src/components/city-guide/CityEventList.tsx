"use client";

import { Calendar, CurrencyCny, MapPin, Ticket } from "@phosphor-icons/react";
import type { CityEvent } from "@/types/city-guide";

interface CityEventListProps {
  events: CityEvent[];
}

export function CityEventList({ events }: CityEventListProps) {
  const getCategoryColor = (category: string) => {
    switch (category) {
      case "music":
        return "bg-purple-100 text-purple-700";
      case "exhibition":
        return "bg-blue-100 text-blue-700";
      case "market":
        return "bg-green-100 text-green-700";
      case "family":
        return "bg-pink-100 text-pink-700";
      case "walk":
        return "bg-amber-100 text-amber-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getCategoryText = (category: string) => {
    const map: Record<string, string> = {
      music: "音乐",
      exhibition: "展览",
      market: "集市",
      family: "亲子",
      walk: "漫步",
      other: "其他",
    };
    return map[category] || category;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      month: "long",
      day: "numeric",
      weekday: "short",
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div
          key={event.id}
          className="bg-card-bg rounded-xl p-4 shadow-paper hover:shadow-paper-hover transition-all duration-300"
        >
          <div className="flex items-start gap-4">
            {/* Date Badge */}
            <div className="flex-shrink-0 w-16 h-16 bg-gradient-to-br from-clay-orange to-clay-orange-dark rounded-xl flex flex-col items-center justify-center text-white">
              <span className="text-xs font-medium">
                {new Date(event.starts_at).toLocaleDateString("zh-CN", { month: "short" })}
              </span>
              <span className="text-2xl font-bold">
                {new Date(event.starts_at).toLocaleDateString("zh-CN", { day: "numeric" })}
              </span>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h3 className="text-lg font-semibold text-ink line-clamp-1">{event.title}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ${getCategoryColor(event.category)}`}>
                  {getCategoryText(event.category)}
                </span>
              </div>

              {event.description && (
                <p className="text-sm text-muted mb-2 line-clamp-2">{event.description}</p>
              )}

              <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
                <div className="flex items-center gap-1">
                  <Calendar className="size-3" />
                  <span>{formatDate(event.starts_at)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>{formatTime(event.starts_at)}</span>
                  {event.ends_at && <span>- {formatTime(event.ends_at)}</span>}
                </div>
                {event.location_name && (
                  <div className="flex items-center gap-1">
                    <MapPin className="size-3" />
                    <span className="line-clamp-1">{event.location_name}</span>
                  </div>
                )}
                {event.price_info && (
                  <div className="flex items-center gap-1">
                    <CurrencyCny className="size-3" />
                    <span>{event.price_info}</span>
                  </div>
                )}
              </div>

              {/* Tags */}
              {event.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {event.tags.slice(0, 3).map((tag, index) => (
                    <span
                      key={index}
                      className="px-2 py-0.5 bg-pine-green/10 text-pine-green text-xs rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Booking Link */}
              {event.booking_url && (
                <a
                  href={event.booking_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 mt-3 text-sm text-clay-orange hover:text-clay-orange-dark transition-colors"
                >
                  <Ticket className="size-4" />
                  预订门票
                </a>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
