// 对生成的 openapi 客户端做轻量补丁 (例如统一导出, 移除多余的 Axios 实例)
import fs from 'fs';
import path from 'path';

const genDir = path.resolve('src/generated');
if(!fs.existsSync(genDir)) process.exit(0);

// 示例：如果生成的 core/axios.ts 创建了一个新的 axios 实例，可提示开发者改为使用现有 apiClient
const coreAxiosFile = path.join(genDir, 'core', 'AxiosHttp.js');
if(fs.existsSync(coreAxiosFile)){
  let content = fs.readFileSync(coreAxiosFile,'utf8');
  if(!content.includes('CUSTOM_API_CLIENT_BOUND')){
    content = '// PATCH: inject custom marker CUSTOM_API_CLIENT_BOUND\n' + content;
    fs.writeFileSync(coreAxiosFile, content, 'utf8');
  }
}
