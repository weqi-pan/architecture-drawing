# 通用领域 Profile

未指定或无法可靠识别行业时使用。本 Profile 不提供任何行业系统清单，只提供开放分类和保守命名规则。

## 分类提示

- 使用者、客户、员工、管理者：`actor`
- 部门、企业、机构、合作主体：`organization`
- 业务活动和能力：`business_capability`
- 面向用户的业务软件：`application`
- 提供共享能力的中枢：`platform`
- 独立运行的信息系统：`system`
- 可复用接口或运行能力：`service`
- 数据主题：`data_domain`
- 数据库、数据湖、文件库：`repository`
- 云、网络、机房、终端：`infrastructure`
- 标准、安全、运维、治理：`security_concern`
- 架构边界外明确交互的主体：`external_system`

## 命名规则

- 优先保留原文正式名称。
- 过长名称可精简显示，但原文名称写入 attributes。
- 不因常见行业做法补充输入未提及的节点。
- 无法分类时使用 `other`，不要强行套入平台或系统。
