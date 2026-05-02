'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui';
import { CommentComposer, CommentList, MemberList, VotePanel } from '@/components/collaboration';
import { getShareInfo, joinShare } from '@/lib/api';

export default function SharePage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [loading, setLoading] = useState(true);
  const [joined, setJoined] = useState(false);
  const [memberName, setMemberName] = useState('');
  const [shareData, setShareData] = useState<any>(null);

  // 模拟数据
  const mockComments = [
    {
      id: '1',
      author: '小明',
      content: '晚餐能不能再清淡一点？',
      createdAt: new Date(Date.now() - 3600000).toISOString(),
      likes: 2,
    },
    {
      id: '2',
      author: '小红',
      content: '这个路线看起来不错，时间安排很合理',
      createdAt: new Date(Date.now() - 1800000).toISOString(),
      likes: 5,
    },
  ];

  const mockMembers = [
    { id: '1', name: '小明', status: 'joined' as const, joinedAt: new Date(Date.now() - 7200000).toISOString() },
    { id: '2', name: '小红', status: 'joined' as const, joinedAt: new Date(Date.now() - 3600000).toISOString() },
  ];

  useEffect(() => {
    // 加载分享信息
    const loadShareInfo = async () => {
      try {
        setLoading(true);
        // const data = await getShareInfo(token);
        // setShareData(data);

        // 模拟数据
        await new Promise(resolve => setTimeout(resolve, 1000));
        setShareData({
          title: '桂林公园 · 街区咖啡线 · 半日行程',
          description: '轻松的半日游路线',
        });
      } catch (error) {
        console.error('Failed to load share info:', error);
      } finally {
        setLoading(false);
      }
    };

    loadShareInfo();
  }, [token]);

  // 加入分享
  const handleJoin = async () => {
    if (!memberName.trim()) {
      return;
    }

    try {
      // await joinShare(token, { nickname: memberName });
      setJoined(true);
    } catch (error) {
      console.error('Failed to join:', error);
    }
  };

  // 提交评论
  const handleComment = async (content: string) => {
    console.log('Submitting comment:', content);
    // 实际应用中应该调用 API
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-paper-bg flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-clay-orange mb-4"></div>
          <p className="text-muted">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper-bg">
      {/* 顶部导航 */}
      <header className="bg-card-bg border-b border-line p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-ink">半日游笺</h1>
          <div className="text-sm text-muted">
            {shareData?.title || '分享的路线'}
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <div className="max-w-4xl mx-auto p-6">
        {/* 欢迎信息 */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-ink mb-2">
            小明邀请你看看这张半日路书
          </h2>
          <p className="text-muted">
            {shareData?.description || '轻松的半日游路线，适合朋友同行'}
          </p>
        </div>

        {/* 方案摘要 */}
        <div className="card-paper p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-ink">3.5h</div>
              <div className="text-xs text-muted">总时长</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-ink">3.2km</div>
              <div className="text-xs text-muted">总距离</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-ink">¥50-100</div>
              <div className="text-xs text-muted">预算</div>
            </div>
          </div>
        </div>

        {/* 加入/内容区域 */}
        {!joined ? (
          <div className="card-paper p-6 mb-6">
            <h3 className="text-lg font-bold text-ink mb-4">加入同行</h3>
            <div className="max-w-md mx-auto">
              <input
                type="text"
                value={memberName}
                onChange={(e) => setMemberName(e.target.value)}
                placeholder="输入你的昵称"
                className="w-full p-3 border border-line rounded-xl mb-4 focus:outline-none focus:border-clay-orange"
              />
              <div className="flex gap-2 justify-center">
                <Button variant="secondary" onClick={() => router.back()}>
                  取消
                </Button>
                <Button
                  variant="primary"
                  onClick={handleJoin}
                  disabled={!memberName.trim()}
                >
                  加入同行
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 投票 */}
            <VotePanel />

            {/* 成员列表 */}
            <MemberList members={mockMembers} />

            {/* 同行小札 */}
            <div className="space-y-4">
              <CommentList comments={mockComments} />
              <CommentComposer onSubmit={handleComment} />
            </div>

            {/* 当前路线 */}
            <div className="card-paper p-6">
              <h3 className="text-sm font-bold text-ink mb-4">当前分享的路线</h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-ink">14:00 出发</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-clay-orange"></div>
                  <span className="text-ink">14:40 桂林公园</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-clay-orange"></div>
                  <span className="text-ink">15:30 街区咖啡</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-pine-green"></div>
                  <span className="text-ink">16:40 返回</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 页脚 */}
      <footer className="text-center py-8 text-sm text-muted">
        <p>城市很大，半日刚好。我们帮你记下这一段刚刚好的时光。</p>
      </footer>
    </div>
  );
}