# 连连支付登录验证

## Page URL
https://global.lianlianpay.com/signin

## Credentials
- identifier_env: LOGIN_USERNAME
- password_env: LOGIN_PASSWORD
- note: 本地最省事的方式是在你自己的 requirement 文件里直接写 `identifier` / `password`
- note: 如果 requirement 没写明文，则会回退到 `.env` 中的 `LOGIN_USERNAME` / `LOGIN_PASSWORD`
- note: 仓库提交的官方样例继续只保留占位符，不保存真实账号密码

## Goal
验证用户能够从登录页成功登录并进入主界面。

## Execution Boundary
- 仅打开登录页面
- 仅填写用户名输入框
- 仅填写密码输入框
- 仅点击登录按钮
- 如出现额外验证（如短信验证码），等待用户手动完成
- 检测到主界面成功信号后立即停止
- 禁止点击菜单、导航到业务页面、编辑个人资料或退出登录

## Acceptance Criteria
1. 登录页面正常加载，显示用户名输入框、密码输入框和登录按钮。
2. 使用有效凭证能够成功提交登录请求。
3. 如需手动验证，流程等待但不尝试自动绕过。
4. 只有当 `LianLian` 标志在主界面可见时，才算测试成功。
5. 检测到 `LianLian` 标志后，自动化流程立即停止，不执行任何额外操作。
