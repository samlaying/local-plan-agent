import type {
  CityArticleListResponse,
  CityEventListResponse,
  CityGuideHomeResponse,
  CityRouteListResponse,
} from "@/types/city-guide";
import type {
  CompanionRecordDetail,
  CompanionRecordListResponse,
} from "@/types/companion-records";
import type {
  CreateCollectionRequest,
  CreateInspirationRequest,
  InspirationCollection,
  InspirationCollectionListResponse,
  InspirationItem,
  InspirationListResponse,
} from "@/types/inspirations";
import type {
  CreateJournalFromTripMapRequest,
  JournalListResponse,
  TravelJournalDetail,
  UpdateJournalRequest,
} from "@/types/journals";

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

// ==================== JOURNALS API ====================

export async function getJournals(params?: {
  status?: string;
  scene?: string;
  tag?: string;
  keyword?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}): Promise<JournalListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/journals${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function getJournalDetail(journalId: string): Promise<TravelJournalDetail> {
  return apiRequest(`/journals/${journalId}`);
}

export async function createJournalFromTripMap(
  request: CreateJournalFromTripMapRequest
): Promise<TravelJournalDetail> {
  return apiRequest("/journals/from-trip-map", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function updateJournal(
  journalId: string,
  request: UpdateJournalRequest
): Promise<TravelJournalDetail> {
  return apiRequest(`/journals/${journalId}`, {
    method: "PATCH",
    body: JSON.stringify(request),
  });
}

export async function archiveJournal(journalId: string): Promise<TravelJournalDetail> {
  return apiRequest(`/journals/${journalId}/archive`, {
    method: "PATCH",
  });
}

// ==================== INSPIRATIONS API ====================

export async function getInspirations(params?: {
  type?: string;
  category?: string;
  tag?: string;
  keyword?: string;
  city?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}): Promise<InspirationListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/inspirations${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function createInspiration(
  request: CreateInspirationRequest
): Promise<InspirationItem> {
  return apiRequest("/inspirations", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getInspirationCollections(): Promise<InspirationCollectionListResponse> {
  return apiRequest("/inspiration-collections");
}

export async function createInspirationCollection(
  request: CreateCollectionRequest
): Promise<InspirationCollection> {
  return apiRequest("/inspiration-collections", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function addInspirationToCollection(
  collectionId: string,
  inspiration_id: string
): Promise<void> {
  return apiRequest(`/inspiration-collections/${collectionId}/items`, {
    method: "POST",
    body: JSON.stringify({ inspiration_id }),
  });
}

// ==================== CITY GUIDE API ====================

export async function getCityGuideHome(params?: { city?: string; district?: string }): Promise<CityGuideHomeResponse> {
  const qs = new URLSearchParams();
  if (params?.city) qs.set("city", params.city);
  if (params?.district) qs.set("district", params.district);

  return apiRequest(`/city-guide/home${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function getCityArticles(params?: {
  category?: string;
  tag?: string;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<CityArticleListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/city-guide/articles${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function getCityArticleDetail(articleId: string) {
  return apiRequest(`/city-guide/articles/${articleId}`);
}

export async function saveArticleToInspirations(articleId: string) {
  return apiRequest(`/city-guide/articles/${articleId}/save-to-inspirations`, {
    method: "POST",
  });
}

export async function getCityRoutes(params?: {
  route_type?: string;
  tag?: string;
  page?: number;
  page_size?: number;
}): Promise<CityRouteListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/city-guide/routes${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function getCityEvents(params?: {
  from?: string;
  to?: string;
  city?: string;
  district?: string;
}): Promise<CityEventListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/city-guide/events${qs.toString() ? `?${qs.toString()}` : ""}`);
}

// ==================== COMPANION RECORDS API ====================

export async function getCompanionRecords(params?: {
  user_id?: string;
  status?: string;
  scene?: string;
  has_feedback?: boolean;
  page?: number;
  page_size?: number;
}): Promise<CompanionRecordListResponse> {
  const qs = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null) qs.set(key, String(value));
  });

  return apiRequest(`/collaboration/records${qs.toString() ? `?${qs.toString()}` : ""}`);
}

export async function getCompanionRecordDetail(groupId: string): Promise<CompanionRecordDetail> {
  return apiRequest(`/collaboration/records/${groupId}`);
}
