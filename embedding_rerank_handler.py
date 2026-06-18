"""
Embedding 和 Rerank 处理模块

提供文本向量化和重排序功能，基于 text-embedding-inference 开源方案
"""

from typing import List, Dict, Optional, Union
import logging
import requests

logger = logging.getLogger(__name__)


class EmbeddingRerankHandler:
    """
    Embedding 和 Rerank 处理器

    封装对 text-embedding-inference 部署的 embedding 和 rerank 接口的调用
    """

    def __init__(
            self,
            embedding_url: Optional[str] = None,
            rerank_url: Optional[str] = None,
            batch_size: int = 32,
            default_timeout: int = 30
    ):
        """
        初始化 Embedding 和 Rerank 处理器

        参数:
        - embedding_url: embedding 服务完整URL，如 "http://localhost:8080/embed"
        - rerank_url: rerank 服务完整URL，如 "http://localhost:8081/rerank"
        - batch_size: 批处理大小，默认32
        - default_timeout: 默认请求超时时间（秒），默认30秒

        示例:
        handler = EmbeddingRerankHandler(
            embedding_url="http://localhost:8080/embed",
            rerank_url="http://localhost:8081/rerank",
            batch_size=32
        )
        """
        self.embedding_url = embedding_url
        self.rerank_url = rerank_url
        self.batch_size = batch_size
        self.default_timeout = default_timeout

        logger.info(
            f"EmbeddingRerankHandler initialized - "
            f"embedding_url: {embedding_url}, rerank_url: {rerank_url}, "
            f"batch_size: {batch_size}"
        )

    def _batch_texts(self, texts: List[str], batch_size: int) -> List[List[str]]:
        """
        将文本列表分批

        参数:
        - texts: 文本列表
        - batch_size: 每批的大小

        返回:
        - List[List[str]]: 分批后的文本列表
        """
        batches = []
        for i in range(0, len(texts), batch_size):
            batches.append(texts[i:i + batch_size])
        return batches

    def get_embedding(
            self,
            texts: Union[str, List[str]],
            normalize: bool = True,
            timeout: Optional[int] = None
    ) -> Union[List[float], List[List[float]]]:
        """
        获取文本的 embedding 向量

        参数:
        - texts: 单个文本或文本列表
        - normalize: 是否归一化向量，默认True
        - timeout: 请求超时时间（秒），None表示使用默认超时时间

        返回:
        - 单个文本: List[float] - 向量列表（如1024维）
        - 多个文本: List[List[float]] - 向量列表的列表

        异常:
        - ValueError: embedding_url 未配置
        - requests.RequestException: HTTP 请求失败

        示例:
        # 单个文本
        vector = service.get_embedding("如何配置通讯参数")
        # 返回: [0.1, 0.2, 0.3, ..., 0.9]  # 1024维向量

        # 多个文本
        vectors = service.get_embedding(["文本1", "文本2", "文本3"])
        # 返回: [[0.1, ...], [0.2, ...], [0.3, ...]]
        """
        # 检查配置
        if not self.embedding_url:
            raise ValueError("embedding_url is not configured")

        # 统一处理为列表
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        # 确定超时时间
        timeout = timeout or self.default_timeout
        url = self.embedding_url

        # 分批处理
        batches = self._batch_texts(texts, self.batch_size)
        all_embeddings = []

        logger.info(f"Processing {len(texts)} texts in {len(batches)} batches (batch_size={self.batch_size})")

        try:
            for batch_idx, batch in enumerate(batches, 1):
                logger.debug(f"Processing batch {batch_idx}/{len(batches)}, size: {len(batch)}")

                # 构建请求
                payload = {
                    "inputs": batch,
                    "normalize": normalize
                }

                response = requests.post(
                    url,
                    json=payload,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                # 解析响应
                batch_embeddings = response.json()
                all_embeddings.extend(batch_embeddings)

                logger.debug(f"Batch {batch_idx} completed, got {len(batch_embeddings)} embeddings")

            logger.info(
                f"Got embeddings for {len(texts)} texts, dimension: {len(all_embeddings[0]) if all_embeddings else 0}")

            # 如果是单个文本，返回单个向量
            if is_single:
                return all_embeddings[0]
            else:
                return all_embeddings

        except requests.exceptions.RequestException as e:
            logger.error(f"Embedding API request failed: {e}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse embedding response: {e}")
            raise ValueError(f"Invalid embedding response format: {e}")

    def rerank(
            self,
            query: str,
            documents: List[str],
            top_n: Optional[int] = None,
            timeout: Optional[int] = None,
            return_text: bool = True
    ) -> List[Dict]:
        """
        对文档列表进行重排序

        参数:
        - query: 查询文本
        - documents: 文档列表
        - top_n: 返回前N个结果，None表示返回全部，默认None
        - timeout: 请求超时时间（秒），None表示使用默认超时时间
        - return_text: 是否在结果中包含原始文本，默认True

        返回:
        - List[Dict]: 重排序后的结果列表，按分数从高到低排序
          [
              {"index": 0, "score": 0.95, "text": "文档1"},  # return_text=True
              {"index": 2, "score": 0.87, "text": "文档3"},
              ...
          ]
          或
          [
              {"index": 0, "score": 0.95},  # return_text=False
              {"index": 2, "score": 0.87},
              ...
          ]

        异常:
        - ValueError: rerank_url 未配置或参数错误
        - requests.RequestException: HTTP 请求失败

        示例:
        query = "如何配置EtherCAT通讯"
        documents = [
            "EtherCAT通讯配置步骤...",
            "Modbus通讯说明...",
            "EtherCAT故障排查..."
        ]

        results = service.rerank(query, documents, top_n=2)
        # 返回:
        # [
        #     {"index": 0, "score": 0.95, "text": "EtherCAT通讯配置步骤..."},
        #     {"index": 2, "score": 0.87, "text": "EtherCAT故障排查..."}
        # ]
        """
        # 检查配置
        if not self.rerank_url:
            raise ValueError("rerank_url is not configured")

        # 参数校验
        if not query:
            raise ValueError("query cannot be empty")

        if not documents:
            logger.warning("documents list is empty, returning empty result")
            return []

        # 确定超时时间
        timeout = timeout or self.default_timeout
        url = self.rerank_url

        # 分批处理
        batches = self._batch_texts(documents, self.batch_size)
        all_results = []

        logger.info(f"Reranking {len(documents)} documents in {len(batches)} batches (batch_size={self.batch_size})")

        try:
            for batch_idx, batch in enumerate(batches):
                batch_offset = batch_idx * self.batch_size
                logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)}, size: {len(batch)}")

                # 构建请求（每批不限制top_n，获取所有结果）
                payload = {
                    "query": query,
                    "texts": batch
                }

                response = requests.post(
                    url,
                    json=payload,
                    timeout=timeout,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                # 解析响应并调整index
                batch_results = response.json()
                for item in batch_results:
                    # 调整index为全局index
                    item["index"] = item["index"] + batch_offset
                    all_results.append(item)

                logger.debug(f"Batch {batch_idx + 1} completed, got {len(batch_results)} results")

            # 按score降序排序
            all_results.sort(key=lambda x: x["score"], reverse=True)

            # 如果指定了top_n，只保留前N个
            if top_n is not None:
                all_results = all_results[:top_n]

            # 根据参数决定是否添加原始文本
            if return_text:
                results_with_text = []
                for item in all_results:
                    index = item["index"]
                    score = item["score"]
                    results_with_text.append({
                        "index": index,
                        "score": score,
                        "text": documents[index]
                    })
                results = results_with_text
            else:
                results = all_results

            logger.info(f"Reranked {len(documents)} documents, returned {len(results)} results")

            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Rerank API request failed: {e}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse rerank response: {e}")
            raise ValueError(f"Invalid rerank response format: {e}")

    def health_check(self) -> Dict[str, bool]:
        """
        检查 embedding 和 rerank 服务的健康状态

        返回:
        - Dict[str, bool]: 各服务的健康状态
          {
              "embedding": True/False,
              "rerank": True/False
          }

        注意: 此方法尝试调用实际的 API 端点来验证服务是否可用
        """
        status = {
            "embedding": False,
            "rerank": False
        }

        # 检查 embedding 服务 - 直接调用服务端点
        if self.embedding_url:
            try:
                response = requests.get(self.embedding_url, timeout=5)
                status["embedding"] = response.status_code in [200, 405]  # 405 表示方法不允许但服务存在
            except Exception as e:
                logger.warning(f"Embedding service health check failed: {e}")
                status["embedding"] = False

        # 检查 rerank 服务 - 直接调用服务端点
        if self.rerank_url:
            try:
                response = requests.get(self.rerank_url, timeout=5)
                status["rerank"] = response.status_code in [200, 405]  # 405 表示方法不允许但服务存在
            except Exception as e:
                logger.warning(f"Rerank service health check failed: {e}")
                status["rerank"] = False

        return status
