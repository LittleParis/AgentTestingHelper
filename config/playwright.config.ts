import { defineConfig, devices } from '@playwright/test';
import { config } from 'dotenv';
import path from 'path';

// 加载 .env 文件
config();

// 浏览器下载到项目目录，避免占用 C 盘空间
process.env.PLAYWRIGHT_BROWSERS_PATH = process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(__dirname, 'browsers');

export default defineConfig({
  testDir: './midscene_run/generated',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 60000,  // 每个测试最长 60 秒
  reporter: [
    ['list'],
    ['allure-playwright', { 
      outputFolder: 'allure-results',
      suiteTitle: false,
      detail: true,
      outputFolder: './allure-results'
    }]
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',  // 禁用视频录制，避免需要 ffmpeg
    actionTimeout: 10000,  // 每个操作最长 10 秒
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: undefined,
  // 传递环境变量给 worker
  globalSetup: undefined,
  // 确保环境变量在 worker 中可用
  expect: {
    timeout: 10000,
  },
});
