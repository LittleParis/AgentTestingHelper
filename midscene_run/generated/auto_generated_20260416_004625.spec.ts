/**
 * 自动生成的 Midscene 测试脚本
 *
 * 生成时间: 2026-04-16 00:46:25
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
  test("TC_001: 验证使用有效关键词进行搜索并成功跳转", async ({ page, ai }) => {
    // 优先级: high
    // 标签: smoke, positive
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面显示了相关内容");

    // 步骤: 在【搜索输入框】中输入关键词
    await ai("在搜索框中输入 \"Selenium自动化测试\"");
    await ai("验证: 页面显示了相关内容");

    // 步骤: 点击【百度一下搜索按钮】
    await ai("点击搜索按钮");
    await ai("验证: 页面URL发生了变化");

    // 最终验证
    await ai("验证: 页面上显示了搜索结果列表");
  });

  test("TC_002: 验证搜索输入框为空时点击搜索按钮的处理", async ({ page, ai }) => {
    // 优先级: medium
    // 标签: negative, boundary
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 保持【搜索输入框】为空，不输入任何内容
    await ai("在搜索框中输入测试内容");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 点击【百度一下搜索按钮】
    await ai("点击搜索按钮");
    await ai("验证: 页面加载完成且稳定");

    // 最终验证
    await ai("验证: 页面URL发生了变化");
  });

  test("TC_003: 验证搜索特殊字符能否正常跳转", async ({ page, ai }) => {
    // 优先级: medium
    // 标签: positive, special_chars
    // 访问目标页面
    await page.goto("https://www.baidu.com");

    // 步骤: 打开百度首页
    await ai("等待页面加载完成");
    await ai("验证: 页面加载完成且稳定");

    // 步骤: 在【搜索输入框】中输入特殊符号
    await ai("在搜索框中输入 \"@#$%^&*()\"");
    await ai("验证: 页面显示了相关内容");

    // 步骤: 点击【百度一下搜索按钮】
    await ai("点击搜索按钮");
    await ai("验证: 页面URL发生了变化");

    // 最终验证
    await ai("验证: 页面上显示了搜索结果列表");
  });
});