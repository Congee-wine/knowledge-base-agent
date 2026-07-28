# 后端设计

## 模块边界

- `retrieval/chunking`：混合切分与来源定位。
- `integrations/embeddings`：`bge-m3` 适配与模型缓存。
- `workers/embedding_tasks`：独立 `embedding` 队列消费、版本化索引任务。
- `repositories`：版本、分块、向量、范围展开和引用持久化。
- `services/retrieval`：权限过滤、Top 8 召回、阈值过滤和上下文构造。
- 聊天工作流仅调用检索服务，不能直接查询向量表。

## Worker 与模型

使用独立 embedding Worker 镜像/队列，避免 PyTorch 和模型加载阻塞文档解析 Worker。模型在 Worker 首个任务中懒加载为进程内单例；Hugging Face 缓存目录挂载为持久卷。初期每个 embedding Worker 并发为 1，避免重复模型副本与显存/内存竞争。

## 版本化索引

更新在新文档版本下生成完整分块和向量，全部成功才原子切换 current 可检索版本；旧版本随后异步清理。删除先在数据库事务中取消当前可检索资格，再投递清理任务，确保删除后不再召回。
