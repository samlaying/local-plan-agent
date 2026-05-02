"use client";

interface InspirationFiltersProps {
  selectedType: string;
  selectedCategory: string;
  onTypeChange: (type: string) => void;
  onCategoryChange: (category: string) => void;
}

export function InspirationFilters({
  selectedType,
  selectedCategory,
  onTypeChange,
  onCategoryChange,
}: InspirationFiltersProps) {
  const types = [
    { value: "", label: "全部" },
    { value: "poi", label: "地点" },
    { value: "route", label: "路线" },
    { value: "quote", label: "句子" },
    { value: "photo", label: "照片" },
    { value: "article", label: "文章" },
    { value: "restaurant", label: "餐厅" },
    { value: "activity", label: "活动" },
  ];

  const categories = [
    { value: "", label: "全部" },
    { value: "cafe", label: "咖啡馆" },
    { value: "park", label: "公园" },
    { value: "museum", label: "展览" },
    { value: "family", label: "亲子" },
    { value: "bookstore", label: "书店" },
    { value: "rainy", label: "适合雨天" },
    { value: "photogenic", label: "可拍照" },
  ];

  return (
    <div className="mb-6 space-y-4">
      {/* Type Filters */}
      <div className="flex flex-wrap gap-2">
        {types.map((type) => (
          <button
            key={type.value}
            onClick={() => onTypeChange(type.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedType === type.value
                ? "bg-clay-orange text-white"
                : "bg-white text-muted hover:bg-card-soft"
            }`}
          >
            {type.label}
          </button>
        ))}
      </div>

      {/* Category Filters */}
      <div className="flex flex-wrap gap-2">
        {categories.map((category) => (
          <button
            key={category.value}
            onClick={() => onCategoryChange(category.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedCategory === category.value
                ? "bg-pine-green text-white"
                : "bg-white text-muted hover:bg-card-soft"
            }`}
          >
            {category.label}
          </button>
        ))}
      </div>
    </div>
  );
}