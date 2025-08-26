// TODO: 重命名此文件为 main.ts 并更新引用
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
import './rum.ts';
// 全局引入 KaTeX 样式，尽量在 Tailwind 之前导入以减少被覆盖的风险
import 'katex/dist/katex.min.css';
// 导入Element Plus样式
import 'element-plus/dist/index.css';
import './style/tailwind.css';

// 全局注册Element Plus图标
import * as ElementPlusIconsVue from '@element-plus/icons-vue';

const app = createApp(App);

// 注册所有Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.use(createPinia());
app.use(router);
app.mount('#app');
