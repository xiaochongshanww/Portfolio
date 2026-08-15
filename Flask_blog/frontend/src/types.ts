/**
 * 项目内共享的数据类型定义。
 * 部分字段与 src/generated/ 自动生成的模型重叠，此处补充视图层使用的扩展字段。
 */

export interface User {
  id: number;
  email?: string;
  nickname?: string;
  avatar?: string;
  role?: string;
  bio?: string;
  social_links?: string;
  created_at?: string;
}

export interface Category {
  id: number;
  name?: string;
  slug?: string;
  parent_id?: number | null;
  description?: string;
  article_count?: number;
  media_count?: number;
  visibility?: string;
}

export interface Tag {
  id: number;
  name: string;
  slug?: string;
  description?: string;
  article_count?: number;
}

export interface ArticleAuthor {
  id: number;
  name?: string;
  nickname?: string;
  email?: string;
  avatar?: string;
  bio?: string;
}

export interface Article {
  id: number;
  title: string;
  slug?: string;
  status?: string;
  summary?: string;
  content_md?: string;
  content_html?: string;
  seo_title?: string;
  seo_desc?: string;
  featured_image?: string;
  category_id?: number | null;
  category?: string | Category | null;
  author?: ArticleAuthor | null;
  tags?: string[];
  scheduled_at?: string | null;
  published_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  views_count?: number;
  likes_count?: number;
  bookmarks_count?: number;
  comments_count?: number;
  content_excerpt?: string;
  is_liked?: boolean;
  is_bookmarked?: boolean;
  score?: number;
  excerpt?: string;
  highlight?: { content?: string };
}

export interface Comment {
  id: number;
  article_id?: number;
  parent_id?: number | null;
  user_id?: number;
  author_name?: string;
  user?: User | null;
  content: string;
  status?: string;
  created_at?: string;
  children?: Comment[];
}

export interface BackupRecord {
  id: number;
  backup_id?: string;
  backup_type?: string;
  status?: string;
  progress?: number;
  file_path?: string;
  file_size?: number;
  compressed_size?: number;
  compression_ratio?: number;
  files_count?: number;
  databases_count?: number;
  encryption_enabled?: boolean;
  checksum?: string;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  duration?: number;
  error_message?: string;
  storage_providers?: Record<string, { status?: string; description?: string }>;
  extra_data?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface RestoreRecord {
  id: number;
  restore_id?: string;
  restore_type?: string;
  status?: string;
  progress?: number;
  status_message?: string;
  target_path?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  restored_files_count?: number;
  restored_databases_count?: number;
  backup_info?: {
    backup_id?: string;
    backup_type?: string;
    file_size?: number;
    created_at?: string;
  };
  _cancelling?: boolean;
  [key: string]: unknown;
}

export interface MediaFile {
  id: number;
  filename?: string;
  original_name?: string;
  file_path?: string;
  file_size?: number;
  mime_type?: string;
  media_type?: string;
  url?: string;
  title?: string;
  alt_text?: string;
  description?: string;
  tags?: string[];
  owner_id?: number;
  owner_name?: string;
  width?: number;
  height?: number;
  folder_id?: number | null;
  created_at?: string;
  variants?: {
    variants?: Array<{ label: string; url?: string; width?: number; height?: number }>;
  };
  [key: string]: unknown;
}

export interface LogEntry {
  id: number;
  timestamp?: string;
  level?: string;
  source?: string;
  message?: string;
  user_id?: number | null;
  user_name?: string;
  endpoint?: string;
  method?: string;
  status_code?: number | null;
  duration_ms?: number | null;
  request_id?: string;
  [key: string]: unknown;
}
