"use client";

import { useState, useEffect } from "react";
import { Users, Clock, ChatCircle, CheckCircle, Warning, Circle } from "@phosphor-icons/react";
import * as api from "@/lib/api";
import type { CompanionRecord, CompanionRecordDetail as CompanionRecordDetailType } from "@/types/companion-records";
import { CompanionRecordList } from "@/components/companions/CompanionRecordList";
import { CompanionRecordDetail } from "@/components/companions/CompanionRecordDetail";

export default function CompanionsPage() {
  const [records, setRecords] = useState<CompanionRecord[]>([]);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<CompanionRecordDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");

  useEffect(() => {
    loadRecords();
  }, [filterStatus]);

  const loadRecords = async () => {
    try {
      setLoading(true);
      const response = await api.getCompanionRecords({
        status: filterStatus || undefined,
      });
      setRecords(response.items || []);

      // Auto-select first record if available
      if (response.items && response.items.length > 0 && !selectedRecordId) {
        setSelectedRecordId(response.items[0].group.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  const loadRecordDetail = async (groupId: string) => {
    try {
      const response = await api.getCompanionRecordDetail(groupId);
      setSelectedRecord(response);
    } catch (err) {
      console.error("加载详情失败:", err);
    }
  };

  useEffect(() => {
    if (selectedRecordId) {
      loadRecordDetail(selectedRecordId);
    }
  }, [selectedRecordId]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "text-success bg-success/10";
      case "has_feedback":
        return "text-warning bg-warning/10";
      case "waiting_confirmation":
        return "text-clay-orange bg-clay-orange/10";
      case "completed":
        return "text-muted bg-muted/10";
      default:
        return "text-muted bg-muted/10";
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case "active":
        return "正在同行";
      case "has_feedback":
        return "有反馈";
      case "waiting_confirmation":
        return "待确认";
      case "completed":
        return "已结束";
      case "cancelled":
        return "已取消";
      default:
        return status;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return Circle;
      case "has_feedback":
        return Warning;
      case "waiting_confirmation":
        return Clock;
      case "completed":
        return CheckCircle;
      default:
        return Circle;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-ink mb-2">同行记录</h1>
        <p className="text-muted">谁与你一起走过这座城，那些同行的小意见也值得被记住。</p>
      </div>

      {/* Status Filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilterStatus("")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filterStatus === ""
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          全部
        </button>
        <button
          onClick={() => setFilterStatus("active")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filterStatus === "active"
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          正在同行
        </button>
        <button
          onClick={() => setFilterStatus("has_feedback")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filterStatus === "has_feedback"
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          有反馈
        </button>
        <button
          onClick={() => setFilterStatus("waiting_confirmation")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filterStatus === "waiting_confirmation"
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          待确认
        </button>
        <button
          onClick={() => setFilterStatus("completed")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filterStatus === "completed"
              ? "bg-clay-orange text-white"
              : "bg-white text-muted hover:bg-card-soft"
          }`}
        >
          已结束
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-card-bg rounded-xl p-4 animate-pulse">
                <div className="h-6 bg-card-soft rounded mb-2" />
                <div className="h-4 bg-card-soft rounded w-2/3" />
              </div>
            ))}
          </div>
          <div className="lg:col-span-2">
            <div className="bg-card-bg rounded-xl p-6 animate-pulse">
              <div className="h-8 bg-card-soft rounded mb-4" />
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-4 bg-card-soft rounded" />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-danger/10 border border-danger text-danger px-6 py-4 rounded-xl">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && records.length === 0 && (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-card-soft rounded-full mb-4">
            <Users className="size-8 text-muted" />
          </div>
          <h3 className="text-xl font-semibold text-ink mb-2">还没有同行记录</h3>
          <p className="text-muted mb-6">开始规划行程，邀请朋友一起探索城市</p>
          <button
            onClick={() => (window.location.href = "/")}
            className="inline-flex items-center gap-2 px-6 py-3 bg-clay-orange text-white rounded-xl hover:bg-clay-orange-dark transition-colors"
          >
            创建新行程
          </button>
        </div>
      )}

      {/* Main Content */}
      {!loading && records.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Record List */}
          <div className="lg:col-span-1">
            <CompanionRecordList
              records={records}
              selectedRecordId={selectedRecordId}
              onSelectRecord={setSelectedRecordId}
              getStatusColor={getStatusColor}
              getStatusText={getStatusText}
              getStatusIcon={getStatusIcon}
            />
          </div>

          {/* Record Detail */}
          <div className="lg:col-span-2">
            {selectedRecord ? (
              <CompanionRecordDetail record={selectedRecord} />
            ) : (
              <div className="bg-card-bg rounded-xl p-6 text-center text-muted">
                选择一条记录查看详情
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
