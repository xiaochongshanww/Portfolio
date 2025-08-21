// TODO: 重命名此文件为 main.ts 并更新引用
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import router from './router';
import App from './App.vue';
import './rum.ts';
import './style/tailwind.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
