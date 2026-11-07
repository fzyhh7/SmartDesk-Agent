"""RAG 数据层：PDF 解析 / 结构感知切分 / Embedding / Milvus 混合检索 + Cross-Encoder 精排。

统一入口在 `backend/app/agents/knowledge.py`（两阶段漏斗：Milvus RRF 粗排 → gte-rerank-v2 精排）。
底下换向量库、换 embedding 或精排模型都不影响上层图结构。
"""
