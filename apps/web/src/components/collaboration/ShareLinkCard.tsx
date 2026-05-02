'use client';

import React, { useState, useCallback } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';
import { CheckCircleIcon } from '../icons';
import { cn } from '@/lib/utils';

interface ShareLinkCardProps {
  shareUrl?: string;
  onCreateShare?: () => Promise<string>;
}

export const ShareLinkCard: React.FC<ShareLinkCardProps> = ({
  shareUrl: initialUrl = '',
  onCreateShare
}) => {
  const [shareUrl, setShareUrl] = useState(initialUrl);
  const [copied, setCopied] = useState(false);
  const [creating, setCreating] = useState(false);

  // 模拟创建分享链接
  const handleCreateShare = async () => {
    if (shareUrl) return;

    try {
      setCreating(true);

      if (onCreateShare) {
        const url = await onCreateShare();
        setShareUrl(url);
      } else {
        // 默认模拟
        await new Promise(resolve => setTimeout(resolve, 1000));
        const mockUrl = `${window.location.origin}/share/route/${Math.random().toString(36).substring(7)}`;
        setShareUrl(mockUrl);
      }
    } catch (error) {
      console.error('Failed to create share link:', error);
    } finally {
      setCreating(false);
    }
  };

  // 复制链接
  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [shareUrl]);

  return (
    <div className="card-paper p-6">
      <h3 className="text-lg font-bold text-ink mb-4">分享你的路线给同行</h3>

      {/* 路线信息 */}
      {shareUrl && (
        <div className="mb-4 p-4 bg-card-soft rounded-xl">
          <div className="text-sm text-muted mb-1">路线名</div>
          <div className="font-medium text-ink">桂林公园 · 街区咖啡线 · 半日行程</div>
        </div>
      )}

      {/* 分享链接 */}
      <div className="mb-4">
        <div className="text-sm text-muted mb-2">分享链接：</div>
        <div className="flex gap-2">
          <div className="flex-1 p-3 bg-card-bg border border-line rounded-xl text-sm text-ink break-all">
            {shareUrl || '点击下方按钮生成分享链接'}
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={shareUrl ? handleCopy : handleCreateShare}
            loading={creating}
          >
            {shareUrl ? (copied ? '已复制' : '复制链接') : '生成链接'}
          </Button>
        </div>
      </div>

      {/* 分享渠道 */}
      <div className="mb-4">
        <div className="text-sm text-muted mb-2">分享渠道：</div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopy}
            disabled={!shareUrl}
          >
            复制链接
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!shareUrl}
          >
            微信
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!shareUrl}
          >
            朋友圈
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!shareUrl}
          >
            QQ
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!shareUrl}
          >
            钉钉
          </Button>
        </div>
      </div>

      {/* 复制成功提示 */}
      {copied && (
        <div className="flex items-center gap-2 text-sm text-pine-green animate-fade-up">
          <CheckCircleIcon className="w-4 h-4" />
          <span>链接已复制到剪贴板</span>
        </div>
      )}
    </div>
  );
};