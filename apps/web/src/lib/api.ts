// API 客户端工具函数
// 使用 Next.js rewrite 规则：/backend-api/:path* -> http://localhost:8000/api/:path*

// 通用请求函数
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `/backend-api${endpoint}`;

  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return await response.json() as T;
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// 具体的 API 调用函数

// 1. 健康检查
export async function checkHealth(): Promise<{ status: string }> {
  return apiRequest<{ status: string }>('/health');
}

// 2. 生成计划预览
export async function generatePlansPreview(request: {
  query: string;
  location: {
    city: string;
    address: string;
    lat: number;
    lng: number;
  };
}) {
  return apiRequest('/plans/preview', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 3. 创建协作地图
export async function createCollaborationMap(request: {
  plan_id: string;
  title: string;
  description?: string;
}) {
  return apiRequest('/collaboration/maps', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 4. 获取协作地图详情
export async function getCollaborationMap(tripMapId: string) {
  return apiRequest(`/collaboration/maps/${tripMapId}`);
}

// 5. 更新站点状态
export async function updateStopStatus(
  stopId: string,
  status: 'pending' | 'in_progress' | 'completed'
) {
  return apiRequest(`/collaboration/maps/stops/${stopId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// 6. 创建协作群组
export async function createCollaborationGroup(request: {
  trip_map_id: string;
  name: string;
  description?: string;
}) {
  return apiRequest('/collaboration/groups', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 7. 创建分享链接
export async function createShareLink(groupId: string) {
  return apiRequest(`/collaboration/groups/${groupId}/share-links`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

// 8. 获取分享信息
export async function getShareInfo(token: string) {
  return apiRequest(`/collaboration/shares/${token}`);
}

// 9. 加入分享
export async function joinShare(token: string, request: {
  nickname: string;
  avatar?: string;
}) {
  return apiRequest(`/collaboration/shares/${token}/join`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 10. 发布评论
export async function postComment(groupId: string, request: {
  member_id: string;
  content: string;
}) {
  return apiRequest(`/collaboration/groups/${groupId}/comments`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 11. 投票
export async function submitVote(groupId: string, request: {
  member_id: string;
  plan_preference: 'plan_a' | 'plan_b' | 'plan_c';
}) {
  return apiRequest(`/collaboration/groups/${groupId}/votes`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// 12. 获取反馈摘要
export async function getFeedbackSummary(groupId: string) {
  return apiRequest(`/collaboration/groups/${groupId}/feedback-summary`);
}

// 13. 获取时间线
export async function getTimeline(planId: string) {
  return apiRequest(`/collaboration/timeline?plan_id=${planId}`);
}