"use client";

import { Folder, Plus, FolderOpen } from "@phosphor-icons/react";
import type { InspirationCollection } from "@/types/inspirations";
import { useState } from "react";

interface CollectionListProps {
  collections: InspirationCollection[];
  onCreateCollection: () => void;
}

export function CollectionList({ collections, onCreateCollection }: CollectionListProps) {
  const [showNewCollectionInput, setShowNewCollectionInput] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [newCollectionDescription, setNewCollectionDescription] = useState("");

  const handleCreateCollection = () => {
    // TODO: 调用创建分组 API
    if (newCollectionName.trim()) {
      console.log("创建分组:", newCollectionName, newCollectionDescription);
      setShowNewCollectionInput(false);
      setNewCollectionName("");
      setNewCollectionDescription("");
    }
  };

  return (
    <div className="bg-card-bg rounded-2xl p-5 shadow-paper">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-ink">我的灵感分组</h3>
        <button
          onClick={() => setShowNewCollectionInput(!showNewCollectionInput)}
          className="p-2 text-clay-orange hover:bg-clay-orange/10 rounded-lg transition-colors"
          title="新建分组"
        >
          <Plus className="size-5" />
        </button>
      </div>

      {/* New Collection Input */}
      {showNewCollectionInput && (
        <div className="mb-4 p-3 bg-card-soft rounded-xl space-y-2">
          <input
            type="text"
            placeholder="分组名称"
            value={newCollectionName}
            onChange={(e) => setNewCollectionName(e.target.value)}
            className="w-full px-3 py-2 bg-white border border-line rounded-lg text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-clay-orange"
          />
          <textarea
            placeholder="描述（可选）"
            value={newCollectionDescription}
            onChange={(e) => setNewCollectionDescription(e.target.value)}
            rows={2}
            className="w-full px-3 py-2 bg-white border border-line rounded-lg text-sm text-ink placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-clay-orange resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreateCollection}
              className="flex-1 px-3 py-1.5 bg-clay-orange text-white rounded-lg text-sm hover:bg-clay-orange-dark transition-colors"
            >
              创建
            </button>
            <button
              onClick={() => {
                setShowNewCollectionInput(false);
                setNewCollectionName("");
                setNewCollectionDescription("");
              }}
              className="flex-1 px-3 py-1.5 bg-white border border-line text-muted rounded-lg text-sm hover:bg-card-soft transition-colors"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* Collections List */}
      {collections.length === 0 ? (
        <div className="text-center py-6">
          <FolderOpen className="size-8 text-muted/30 mx-auto mb-2" />
          <p className="text-sm text-muted">还没有分组</p>
          <p className="text-xs text-muted/60 mt-1">创建分组来整理灵感</p>
        </div>
      ) : (
        <div className="space-y-2">
          {collections.map((collection) => (
            <button
              key={collection.id}
              className="w-full flex items-center gap-3 p-3 bg-card-soft rounded-xl hover:bg-pine-green/10 transition-colors text-left"
            >
              <Folder className="size-5 text-clay-orange" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-ink truncate">{collection.name}</p>
                <p className="text-xs text-muted">{collection.item_count} 个灵感</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}