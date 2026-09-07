// TODO: 重命名此文件为 main.ts 并更新引用
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
// 全局引入 KaTeX 样式，尽量在 Tailwind 之前导入以减少被覆盖的风险
import 'katex/dist/katex.min.css';
// 导入Element Plus样式
import 'element-plus/dist/index.css';
import './style/tailwind.css';
import './style/admin.css';
// P2-E2:挂载前应用记忆的主题,防暗色用户首屏白闪
import { applyThemeFromStorage } from './composables/useTheme';

applyThemeFromStorage();

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.mount('#app');
