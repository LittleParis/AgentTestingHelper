import 'dotenv/config';

/**
 * Midscene 配置文件
 * 用于配置 AI 模型服务
 *
 * 文档: https://midscenejs.com/model-provider.html
 */

// 导出配置，供测试文件使用
export const midsceneConfig = {
  // 使用 OpenAI 兼容 API
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
  modelName: process.env.MIDSCENE_MODEL_NAME || 'gpt-4o',
};

// 验证配置
if (!process.env.OPENAI_API_KEY) {
  console.warn('Warning: OPENAI_API_KEY is not set. Midscene AI features may not work.');
}
