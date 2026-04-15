/**
 * 自动生成的 Midscene 测试脚本
 *
 * 生成时间: 2026-04-15 22:32:26
 * 生成器: MidsceneScriptGenerator
 *
 * 注意: 此文件由程序自动生成，请勿手动修改
 */
import { test as base, expect } from '@playwright/test';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import allure from 'allure-playwright';

// 扩展 test 以使用 Midscene AI fixture
const test = base.extend<{
  ai: any;
  aiAction: any;
  aiTap: any;
  aiInput: any;
  aiAssert: any;
  aiQuery: any;
}>(PlaywrightAiFixture());

test.describe('自动生成的测试用例', () => {
  test("TC_001: 验证使用有效关键词进行正常搜索", async ({ page, ai }) => {
    // 优先级: high
    // 标签: smoke, p1
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 在搜索输入框中输入关键词
    await ai("在搜索框中输入 \"测试工程师\"");
    await ai("验证: 页面显示了相关内容");

    // 步骤: 点击“百度一下”按钮
    await ai("点击搜索按钮");
    await ai("验证: 页面上显示了搜索结果列表");

    // 最终验证
    await ai("验证: 页面上显示了搜索结果列表");
  });

  test("TC_002: 验证搜索输入框为空时的系统处理", async ({ page, ai }) => {
    // 优先级: medium
    // 标签: boundary, p2
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 保持搜索输入框为空，不做任何输入
    await ai("在搜索框中输入测试内容");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 点击“百度一下”按钮
    await ai("点击搜索按钮");
    await ai("验证: 页面URL发生了变化");

    // 最终验证
    await ai("验证: 页面URL发生了变化");
  });

  test("TC_003: 验证搜索特殊字符及URL编码跳转", async ({ page, ai }) => {
    // 优先级: medium
    // 标签: negative, security, p2
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 在搜索输入框中输入特殊字符组合
    await ai("在搜索框中输入 \"@#￥%\"");
    await ai("验证: 页面显示了相关内容");

    // 步骤: 点击“百度一下”按钮
    await ai("点击搜索按钮");
    await ai("验证: 页面URL发生了变化");

    // 最终验证
    await ai("验证: 页面URL发生了变化");
  });
});