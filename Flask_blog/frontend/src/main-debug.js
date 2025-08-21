// 调试版本的 main.js - 逐步添加功能
console.log('🚀 Starting Vue app initialization...');

try {
  console.log('📦 Importing Vue...');
  const { createApp } = await import('vue');
  console.log('✅ Vue imported successfully');

  console.log('📦 Importing Pinia...');
  const { createPinia } = await import('pinia');
  console.log('✅ Pinia imported successfully');

  console.log('📦 Importing Router...');
  const router = await import('./router');
  console.log('✅ Router imported successfully');

  console.log('📦 Importing App component...');
  const App = await import('./App.vue');
  console.log('✅ App component imported successfully');

  console.log('🎨 Importing styles...');
  await import('./style/tailwind.css');
  console.log('✅ Styles imported successfully');

  console.log('🏗️ Creating Vue app...');
  const app = createApp(App.default);
  console.log('✅ Vue app created');

  console.log('🔌 Installing Pinia...');
  app.use(createPinia());
  console.log('✅ Pinia installed');

  console.log('🔌 Installing Router...');
  app.use(router.default);
  console.log('✅ Router installed');

  console.log('🎯 Mounting app to #app...');
  app.mount('#app');
  console.log('🎉 Vue app mounted successfully!');

} catch (error) {
  console.error('❌ Error during app initialization:', error);
  console.error('Stack trace:', error.stack);
  
  // 显示错误给用户
  document.getElementById('app').innerHTML = `
    <div style="padding: 20px; background: #fee; border: 1px solid #fcc; color: #c00; font-family: monospace;">
      <h2>Vue App Initialization Error</h2>
      <p><strong>Error:</strong> ${error.message}</p>
      <details>
        <summary>Full error details</summary>
        <pre>${error.stack}</pre>
      </details>
    </div>
  `;
}