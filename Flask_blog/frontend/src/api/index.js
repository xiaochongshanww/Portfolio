// 统一出口: 绑定生成客户端 + 业务自定义
// 使用 generated 聚合出口（index.ts）
import { OpenAPI } from '../generated';
import * as Services from '../generated';
import { bindGeneratedClient, createServices } from './generatedClientAdapter';

bindGeneratedClient(OpenAPI);
export const API = createServices(Services);

// 用法示例: API.ArticlesService.listArticles();
