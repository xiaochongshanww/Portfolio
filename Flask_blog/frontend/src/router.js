// TODO: 重命名为 router.ts 以获得类型支持
import { createRouter, createWebHistory } from 'vue-router';
// 关键首页等核心路由可直接静态导入；体量较大的视图按需分包
import Home from './views/Home.vue';
import Login from './views/Login.vue';
import NewArticle from './views/NewArticle.vue';
const Register = () => import('./views/Register.vue');
const Profile = () => import('./views/Profile.vue');
// 其余延迟加载
const ArticleDetail = () => import(/* webpackChunkName: 'article-detail' */ './views/ArticleDetail.vue');
const AuthorProfile = () => import(/* webpackChunkName: 'author-profile' */ './views/AuthorProfile.vue');
const SearchPage = () => import(/* webpackChunkName: 'search-page' */ './views/SearchPage.vue');
const CategoryPage = () => import('./views/CategoryPage.vue');
const TagPage = () => import('./views/TagPage.vue');
const CommentsModeration = () => import(/* webpackChunkName: 'comments-moderation' */ './views/CommentsModeration.vue');
const UserAdmin = () => import(/* webpackChunkName: 'user-admin' */ './views/UserAdmin.vue');
const SearchSynonymsAdmin = () => import('./views/SearchSynonymsAdmin.vue');
const MetricsDashboard = () => import('./views/MetricsDashboard.vue');
import { resetMeta } from './composables/useMeta';

// CMS后台相关路由
const AdminLayout = () => import(/* webpackChunkName: 'admin' */ './views/admin/AdminLayout.vue');
const Dashboard = () => import(/* webpackChunkName: 'admin' */ './views/admin/Dashboard.vue');
const ArticleManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/ArticleManagement.vue');
const ArticleReview = () => import(/* webpackChunkName: 'admin' */ './views/admin/ArticleReview.vue');
const CommentManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/CommentManagement.vue');
const CategoryManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/CategoryManagement.vue');
const TagManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/TagManagement.vue');
const UserManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/UserManagement.vue');
const SecurityMonitoring = () => import(/* webpackChunkName: 'admin' */ './views/admin/SecurityMonitoring.vue');
const LogManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/LogManagement.vue');
const SimpleLogManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/SimpleLogManagement.vue');
const SystemPerformance = () => import(/* webpackChunkName: 'admin' */ './views/admin/SystemPerformance.vue');
const SystemSettings = () => import(/* webpackChunkName: 'admin' */ './views/admin/SystemSettings.vue');
const BackupManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/BackupManagement.vue');
const RestoreManagement = () => import(/* webpackChunkName: 'admin' */ './views/admin/RestoreManagement.vue');

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/me/profile', component: Profile },
  { path: '/articles/new', component: NewArticle },
  { path: '/articles/:id/edit', component: NewArticle, props: true, meta: { editMode: true, requiresAuth: true } },
  { path: '/new-article', redirect: '/articles/new' }, // 兼容重定向
  { path: '/article/:slug', component: ArticleDetail, props: true },
  { path: '/author/:id', component: AuthorProfile, props: true },
  { path: '/category/:id', component: CategoryPage, props: true },
  { path: '/tag/:slug', component: TagPage, props: true },
  { path: '/search', component: SearchPage },
  { path: '/categories', component: () => import('./views/CategoriesPage.vue') },
  { path: '/tags', component: () => import('./views/TagsPage.vue') },
  { path: '/icon-test', component: () => import('./views/IconTest.vue') },
  { path: '/tags-test', component: () => import('./views/TagsPageTest.vue') },
  { path: '/archive', component: () => import('./views/ArchivePage.vue') },
  { path: '/hot', component: () => import('./views/HotArticles.vue') },
  { path: '/about', component: () => import('./views/About.vue') },
  
  // CMS后台路由
  {
    path: '/admin',
    component: AdminLayout,
    meta: { requiresAuth: true, requiresRole: ['author', 'editor', 'admin'] },
    children: [
      { path: '', component: Dashboard },
      { path: 'articles', component: ArticleManagement },
      { path: 'articles/:id/edit', component: NewArticle, props: true, meta: { editMode: true } },
      { path: 'articles/review', component: ArticleReview, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'comments', component: CommentManagement, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'categories', component: CategoryManagement, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'tags', component: TagManagement, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'users', component: UserManagement, meta: { requiresRole: ['admin'] } },
      { path: 'security', component: SecurityMonitoring, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'logs', component: LogManagement, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'simple-logs', component: SimpleLogManagement, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'performance', component: SystemPerformance, meta: { requiresRole: ['editor', 'admin'] } },
      { path: 'settings/general', component: SystemSettings, meta: { requiresRole: ['admin'] } },
      { path: 'backup', component: BackupManagement, meta: { requiresRole: ['admin'] } },
      { path: 'restore', component: RestoreManagement, meta: { requiresRole: ['admin'] } },
    ]
  },
  
  // 兼容旧的管理路由
  { path: '/moderation/comments', component: CommentsModeration },
  { path: '/admin/users', component: UserAdmin },
  { path: '/admin/search/synonyms', component: SearchSynonymsAdmin },
  { path: '/admin/metrics', component: MetricsDashboard }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(){ return { top: 0 }; }
});

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 动态导入用户store以避免循环依赖
  const { useUserStore } = await import('./stores/user.js');
  const userStore = useUserStore();
  
  // 初始化认证状态
  if (!userStore.user && userStore.token) {
    await userStore.initAuth();
  }
  
  // 检查需要认证的路由
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    next('/login');
    return;
  }
  
  // 检查角色权限
  if (to.meta.requiresRole && userStore.isAuthenticated) {
    const requiredRoles = to.meta.requiresRole;
    if (!userStore.hasRole(requiredRoles)) {
      next('/'); // 重定向到首页或显示无权限页面
      return;
    }
  }
  
  next();
});

// 路由切换时重置为基础 Meta（具体页面再覆盖）
router.afterEach(()=>{ resetMeta(); });

export default router;
