"use client";

interface CityGuideTabsProps {
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
}

export function CityGuideTabs({ selectedCategory, onCategoryChange }: CityGuideTabsProps) {
  const categories = [
    { value: "", label: "全部" },
    { value: "weekly_feature", label: "本周策展" },
    { value: "neighborhood_walk", label: "街区漫游" },
    { value: "cafe_bookstore", label: "咖啡与书店" },
    { value: "museum_exhibition", label: "展览与博物馆" },
    { value: "family_day", label: "亲子目的地" },
    { value: "rainy_day", label: "雨天备选" },
    { value: "city_calendar", label: "城市日历" },
  ];

  return (
    <div className="flex overflow-x-auto gap-2 pb-2">
      {categories.map((category) => (
        <button
          key={category.value}
          onClick={() => onCategoryChange(category.value)}
          className={`px-5 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
            selectedCategory === category.value
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          {category.label}
        </button>
      ))}
    </div>
  );
}