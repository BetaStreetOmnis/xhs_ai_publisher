# 提醒、热点草稿与人工发布验证 · 2026-10-30

这次变更针对桌面源码及仓库自带的本机 Web/API。它不更新官网部署，也不更新已有的 v2.0.0-rc.2 安装包。

## 行为边界

- 固定内容任务到点只记录并显示提醒；不创建浏览器、不登录、不生成占位图。
- 热点任务只生成一次本地草稿，将正文、图片副本及参考来源存入任务记录。旧重复间隔被忽略。
- 「后台配置 → 提醒与草稿」可打开内容继续编辑，查看热榜链接、搜索摘要及核对提示。打开内容前会确认是否替换首页现有内容。
- 热榜及摘要不是经过核实的事实。生成提示要求不编造亲身体验、数据、采访或引语，仍需要本人核对。
- 旧待执行任务使用新策略。升级前执行中的任务保留为待核验；已有提交记录不会被改成已验证发布，也不会自动重发。
- 桌面发布器在浏览器初始化前拒绝 `auto_publish=true`，直接调用最终提交方法也会拒绝。本机 API 对同样的参数返回 HTTP 400。
- 桌面及 Web 页面提供事实、素材授权、AI 使用的人工核对。API 需显式提供核对字段；这些字段不能代替事实核验，也不会自动设置平台声明。
- 已移除自动化属性隐藏脚本和强制 DOM 动作兜底。人工发布和 AI 声明都不能保证平台审核结果。
- 任务异常会停止调度。检查模型及存储配置后，重新启用任务开关并创建新任务；不自动重试旧任务。

## 离线验证

```bash
venv/bin/python -m pytest -q tests/unit/test_publication_safety.py tests/unit/test_publication_ui.py tests/unit/test_web_access.py
```

68 项通过。覆盖 API 认证、自动提交拒绝、人工核对、排队去重、会话变化、失败及重启、旧任务迁移、提醒只触发一次、热点不创建发布器、草稿持久化和来源保留、图片副本、存储失败、删除后的迟到回调，以及 Qt 控件和草稿载入。测试替换浏览器、账号和模型 I/O，没有真实发布，也没有调用付费模型。

```bash
venv/bin/python -m pytest -q tests/unit -m 'not network and not browser' --maxfail=0
```

扩展检查时 217 项通过，13 项失败；随后补充的迟到回调和来源生成测试在上方相关测试中通过。对未修改的基线 `d76c8fc19b188aa18d75ab1e73a88e189aa9f10e` 使用相同命令得到 201 项通过、相同的 13 项失败。失败全部来自 `test_cover_templates.py` 仍向 `CoverTemplateService.generate_cover` 传入已不支持的 `template_name`，与本次发布流程修改无关。不能据此声称整个测试套件全部通过。

Python 编译检查及 `git diff --check` 通过。未验证真实小红书页面在当前账号上的登录或辅助填写，也未生成新安装包。

## 界面检查

使用隔离运行目录和 Qt offscreen 实际渲染检查了内容提醒、热点草稿、人工核对及任务列表。控件及提示未截断；核对不完整时无法继续填写，未关联账号也能创建提醒。Qt 控件测试单独启动进程，避免旧启动测试的 `QCoreApplication` 干扰窗口测试。

- [内容提醒](assets/manual-publication-20261030/reminder.png)
- [热点草稿](assets/manual-publication-20261030/hotspot-draft.png)
- [人工核对](assets/manual-publication-20261030/review.png)
- [任务列表](assets/manual-publication-20261030/task-list.png)

静态界面检查发现 11 条已有的 Web 页面配色、对比度提示。本次保留现有视觉样式；这不等于页面已通过完整的无障碍验收。
