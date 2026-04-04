"""
中文语义分块系统 - 基于 BGE-large-zh-v1.5
Author: AI Assistant
Date: 2024
"""
import json
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
from dataclasses import dataclass, field
from enum import Enum
import heapq
from collections import defaultdict, deque
import logging
from functools import lru_cache
import time

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """分块策略枚举"""
    SEMANTIC = "semantic"  # 纯语义分块
    HYBRID = "hybrid"  # 混合分块（语义+结构）
    HIERARCHICAL = "hierarchical"  # 层次分块
    DYNAMIC = "dynamic"  # 动态分块


@dataclass
class ChunkConfig:
    """分块配置"""
    max_chunk_tokens: int = 1000
    min_chunk_tokens: int = 100
    overlap_tokens: int = 100
    similarity_threshold: float = 0.75
    topic_shift_threshold: float = 0.3
    max_sentences_per_chunk: int = 15
    min_sentences_per_chunk: int = 2
    use_cache: bool = True
    cache_size: int = 10000
    batch_size: int = 16
    device: str = None


class BGEChineseTokenizer:
    """BGE 中文分词器封装"""

    def __init__(self, model_path: str = r"D:\PythonProject\models\bge-large-zh-v1.5"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)

    def encode(self, text: str) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def decode(self, tokens: List[int]) -> str:
        return self.tokenizer.decode(tokens, skip_special_tokens=True)

    def count_tokens(self, text: str) -> int:
        return len(self.encode(text))

    def batch_encode(self, texts: List[str]) -> List[List[int]]:
        return [self.encode(text) for text in texts]


class ChineseSentenceSplitter:
    """中文句子分割器"""

    def __init__(self):
        # 中文标点符号定义
        self.sentence_end_punct = set(['。', '！', '？', '……', '…', '；'])
        self.comma_punct = set(['，', '、', ',', ';'])
        self.quote_punct = set(['「', '」', '『', '』', '“', '”', '‘', '’'])
        self.bracket_punct = set(['（', '）', '《', '》', '【', '】', '〈', '〉', '[', ']', '(', ')'])

        # 句子分割正则表达式
        self.sentence_pattern = re.compile(
            r'(?<=[。！？;；])\s+|'  # 常规句子结束
            r'(?<=\.\.\.)\s+|'  # 英文省略号
            r'(?<=……)\s+|'  # 中文省略号
            r'\n\s*\n'  # 空行
        )

    def split_sentences(self, text: str) -> List[str]:
        """分割中文句子"""
        if not text:
            return []

        sentences = []
        current_sentence = []
        chars = list(text)

        i = 0
        while i < len(chars):
            char = chars[i]
            current_sentence.append(char)

            # 检查是否句子结束
            if self._is_sentence_end(chars, i):
                sentence = ''.join(current_sentence).strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = []

            i += 1

        # 处理最后一个句子
        if current_sentence:
            sentence = ''.join(current_sentence).strip()
            if sentence:
                sentences.append(sentence)

        return sentences

    def _is_sentence_end(self, chars: List[str], index: int) -> bool:
        """判断当前位置是否是句子结束"""
        if index >= len(chars) - 1:
            return True

        current_char = chars[index]
        next_char = chars[index + 1]

        # 基本句子结束标点
        if current_char in self.sentence_end_punct:
            # 检查是否是省略号的一部分
            if current_char == '…' and index > 0 and chars[index - 1] == '…':
                return False
            if current_char == '…' and index < len(chars) - 1 and chars[index + 1] == '…':
                return False
            return True

        # 引号或括号结束
        if current_char in self.quote_punct or current_char in self.bracket_punct:
            # 后面是空格或换行
            if next_char in [' ', '\n', '\t', '\r']:
                return True

        return False

    def split_paragraphs(self, text: str) -> List[str]:
        """分割段落"""
        paragraphs = []
        current_para = []
        lines = text.split('\n')

        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                current_para.append(stripped_line)
            elif current_para:
                paragraphs.append('\n'.join(current_para))
                current_para = []

        if current_para:
            paragraphs.append('\n'.join(current_para))

        return paragraphs


class BGEChineseEmbedder:
    """BGE 中文嵌入模型"""

    def __init__(self, model_path: str = "bge-large-zh-v1.5",
                 device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"使用设备: {self.device}")

        # 加载模型
        logger.info(f"加载模型: {model_path}")
        # self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        # self.model = AutoModel.from_pretrained(model_name).to(self.device)
        local_model_path = r"D:\PythonProject\models\bge-large-zh-v1.5"
        self.tokenizer = AutoTokenizer.from_pretrained(local_model_path)
        self.model = AutoModel.from_pretrained(local_model_path).to(self.device)
        self.model.eval()

        # 缓存
        self.embedding_cache = {}
        self.batch_cache = {}

    @lru_cache(maxsize=10000)
    def get_embedding_cached(self, text: str) -> np.ndarray:
        """带缓存的嵌入获取"""
        return self._get_embedding_impl(text)

    def _get_embedding_impl(self, text: str) -> np.ndarray:
        """实现嵌入获取"""
        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                return_tensors='pt',
                max_length=512
            ).to(self.device)

            outputs = self.model(**inputs)
            # BGE 建议使用 [CLS] token
            embeddings = outputs.last_hidden_state[:, 0, :]
            embeddings = F.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().numpy()[0]

    def get_embedding(self, text: str, use_cache: bool = True) -> np.ndarray:
        """获取文本嵌入"""
        if not text.strip():
            return np.zeros(1024)  # BGE-large 的维度

        if use_cache:
            return self.get_embedding_cached(text)
        else:
            return self._get_embedding_impl(text)

    def batch_get_embeddings(self, texts: List[str]) -> np.ndarray:
        """批量获取嵌入"""
        if not texts:
            return np.array([])

        with torch.no_grad():
            inputs = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors='pt',
                max_length=512
            ).to(self.device)

            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :]
            embeddings = F.normalize(embeddings, p=2, dim=1)
            return embeddings.cpu().numpy()

    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的余弦相似度"""
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)

        # 检查零向量
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(emb1, emb2) / (norm1 * norm2)
        return float(similarity)

    def compute_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """计算相似度矩阵"""
        n = len(texts)
        embeddings = self.batch_get_embeddings(texts)

        # 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # 避免除以零
        embeddings_normalized = embeddings / norms

        # 计算相似度矩阵
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        return similarity_matrix


class DocumentAnalyzer:
    """文档结构分析器"""

    def __init__(self):
        self.sentence_splitter = ChineseSentenceSplitter()

        # 标题检测模式
        self.heading_patterns = [
            (re.compile(r'^第[一二三四五六七八九十]+章\s+.*'), 1),  # 第X章
            (re.compile(r'^第[一二三四五六七八九十]+节\s+.*'), 2),  # 第X节
            (re.compile(r'^[一二三四五六七八九十]+、\s+.*'), 3),  # 一、
            (re.compile(r'^\d+\.\d+\s+.*'), 3),  # 1.1
            (re.compile(r'^\d+\.\s+.*'), 4),  # 1.
            (re.compile(r'^[•·◦]\s+.*'), 5),  # • 项目符号
        ]

        # 列表检测模式
        self.list_patterns = [
            r'^\s*[-*•·◦]\s+',
            r'^\s*\d+[\.\)]\s+',
            r'^\s*[一二三四五六七八九十]+[、.]\s+',
            r'^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*',
        ]

    def analyze(self, content: str) -> Dict[str, Any]:
        """分析文档结构"""
        # 分割段落
        paragraphs = self.sentence_splitter.split_paragraphs(content)

        analysis = {
            'paragraphs': [],
            'headings': [],
            'lists': [],
            'total_sentences': 0,
            'total_paragraphs': len(paragraphs),
        }

        for para_idx, paragraph in enumerate(paragraphs):
            # 检测是否是标题
            heading_info = self._detect_heading(paragraph)
            if heading_info:
                analysis['headings'].append({
                    'paragraph_index': para_idx,
                    'level': heading_info['level'],
                    'text': heading_info['text'],
                })

            # 分割句子
            sentences = self.sentence_splitter.split_sentences(paragraph)
            analysis['total_sentences'] += len(sentences)

            # 检测是否是列表
            is_list = self._is_list_paragraph(paragraph)

            paragraph_info = {
                'index': para_idx,
                'text': paragraph,
                'sentences': sentences,
                'sentence_count': len(sentences),
                'is_heading': bool(heading_info),
                'is_list': is_list,
                'heading_level': heading_info['level'] if heading_info else None,
            }

            analysis['paragraphs'].append(paragraph_info)

            if is_list:
                analysis['lists'].append({
                    'paragraph_index': para_idx,
                    'items': self._extract_list_items(paragraph),
                })

        return analysis

    def _detect_heading(self, text: str) -> Optional[Dict]:
        """检测标题"""
        lines = text.strip().split('\n')
        if len(lines) != 1:  # 标题通常是单行
            return None

        line = lines[0]
        for pattern, level in self.heading_patterns:
            if pattern.match(line):
                return {
                    'level': level,
                    'text': line,
                }

        # 检查 Markdown 标题
        if line.startswith('#'):
            level = line.count('#', 0, min(6, len(line)))
            return {
                'level': level,
                'text': line.lstrip('#').strip(),
            }

        return None

    def _is_list_paragraph(self, text: str) -> bool:
        """检测是否是列表段落"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) <= 1:
            return False

        # 检查每行是否匹配列表模式
        list_count = 0
        for line in lines:
            if any(re.match(pattern, line) for pattern in self.list_patterns):
                list_count += 1

        # 大多数行都是列表格式
        return list_count >= max(2, len(lines) * 0.7)

    def _extract_list_items(self, text: str) -> List[str]:
        """提取列表项"""
        items = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            # 移除列表标记
            for pattern in self.list_patterns:
                line = re.sub(pattern, '', line)
            items.append(line.strip())

        return items


class SemanticChunker:
    """语义分块器"""

    def __init__(self,
                 embedder: BGEChineseEmbedder,
                 tokenizer: BGEChineseTokenizer,
                 config: Optional[ChunkConfig] = None):
        self.embedder = embedder
        self.tokenizer = tokenizer
        self.config = config or ChunkConfig()
        self.analyzer = DocumentAnalyzer()
        self.sentence_splitter = ChineseSentenceSplitter()

        logger.info(f"初始化语义分块器，配置: {self.config}")

    def chunk(self,
              content: str,
              strategy: ChunkingStrategy = ChunkingStrategy.HYBRID,
              **kwargs) -> List[Dict[str, Any]]:
        """
        主分块函数

        Args:
            content: 输入文本
            strategy: 分块策略
            **kwargs: 覆盖配置参数

        Returns:
            分块列表
        """
        start_time = time.time()

        # 更新配置
        config = self._update_config(kwargs)

        # 选择策略
        if strategy == ChunkingStrategy.SEMANTIC:
            chunks = self._semantic_chunking(content, config)
        elif strategy == ChunkingStrategy.HIERARCHICAL:
            chunks = self._hierarchical_chunking(content, config)
        elif strategy == ChunkingStrategy.DYNAMIC:
            chunks = self._dynamic_chunking(content, config)
        else:  # HYBRID
            chunks = self._hybrid_chunking(content, config)

        # 后处理
        chunks = self._post_process(chunks, content, config)

        # 添加元数据
        final_chunks = self._add_metadata(chunks, config, time.time() - start_time)

        logger.info(f"分块完成: 生成 {len(final_chunks)} 个分块，耗时 {time.time() - start_time:.2f}s")
        return final_chunks

    def _update_config(self, kwargs: Dict) -> ChunkConfig:
        """更新配置"""
        config_dict = self.config.__dict__.copy()
        config_dict.update(kwargs)
        return ChunkConfig(**config_dict)

    def _semantic_chunking(self, content: str, config: ChunkConfig) -> List[Dict]:
        """纯语义分块"""
        sentences = self.sentence_splitter.split_sentences(content)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for i, sentence in enumerate(sentences):
            sentence_tokens = self.tokenizer.count_tokens(sentence)

            # 如果当前分块为空，直接添加
            if not current_chunk:
                current_chunk.append(sentence)
                current_tokens = sentence_tokens
                continue

            # 计算语义相似度
            prev_sentence = current_chunk[-1]
            similarity = self.embedder.compute_similarity(prev_sentence, sentence)

            # 决策是否开始新分块
            should_start_new = (
                    similarity < config.similarity_threshold or  # 语义不相似
                    current_tokens + sentence_tokens > config.max_chunk_tokens or  # token超限
                    self._detect_topic_shift(current_chunk, sentence, config)  # 话题转换
            )

            if should_start_new:
                # 结束当前分块
                if current_chunk:
                    chunk_text = ''.join(current_chunk)
                    chunks.append({
                        'content': chunk_text,
                        'tokens': current_tokens,
                        'sentences': len(current_chunk),
                        'type': 'semantic_chunk'
                    })

                # 开始新分块
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # 继续当前分块
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # 添加最后一个分块
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            chunks.append({
                'content': chunk_text,
                'tokens': current_tokens,
                'sentences': len(current_chunk),
                'type': 'semantic_chunk'
            })

        return chunks

    def _detect_topic_shift(self, current_chunk: List[str],
                            new_sentence: str,
                            config: ChunkConfig) -> bool:
        """检测话题转换"""
        if len(current_chunk) < 2:
            return False

        # 计算当前分块最近两句的主题
        recent_text = ''.join(current_chunk[-2:])
        similarity = self.embedder.compute_similarity(recent_text, new_sentence)

        return similarity < config.topic_shift_threshold

    def _hierarchical_chunking(self, content: str, config: ChunkConfig) -> List[Dict]:
        """层次分块"""
        # 第一层：按段落
        paragraphs = self.sentence_splitter.split_paragraphs(content)
        chunks = []

        for para_idx, paragraph in enumerate(paragraphs):
            para_tokens = self.tokenizer.count_tokens(paragraph)

            # 如果段落太大，进一步分割
            if para_tokens > config.max_chunk_tokens:
                sub_chunks = self._split_large_paragraph(paragraph, config)
                for sub_idx, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        'content': sub_chunk['content'],
                        'tokens': sub_chunk['tokens'],
                        'type': f'subparagraph_{para_idx}_{sub_idx}',
                        'sentences': sub_chunk.get('sentences', 1),
                        'paragraph_index': para_idx,
                    })
            else:
                # 段落大小合适
                sentences = self.sentence_splitter.split_sentences(paragraph)
                chunks.append({
                    'content': paragraph,
                    'tokens': para_tokens,
                    'type': 'paragraph',
                    'sentences': len(sentences),
                    'paragraph_index': para_idx,
                })

        return chunks

    def _split_large_paragraph(self, paragraph: str, config: ChunkConfig) -> List[Dict]:
        """分割大段落"""
        sentences = self.sentence_splitter.split_sentences(paragraph)
        if len(sentences) <= 1:
            return [{
                'content': paragraph,
                'tokens': self.tokenizer.count_tokens(paragraph),
                'sentences': 1
            }]

        # 动态规划找到最优分割点
        n = len(sentences)
        sentence_tokens = [self.tokenizer.count_tokens(s) for s in sentences]

        # 计算句子间的语义相似度
        similarity_matrix = self.embedder.compute_similarity_matrix(sentences)

        # DP 数组：dp[i] 表示前i个句子的最优分块
        dp = [{'score': -1e9, 'chunks': [], 'last': -1} for _ in range(n + 1)]
        dp[0] = {'score': 0, 'chunks': [], 'last': -1}

        for i in range(1, n + 1):
            for j in range(i):
                # 计算从j到i-1的区间
                chunk_sentences = sentences[j:i]
                chunk_text = ''.join(chunk_sentences)
                chunk_tokens = sum(sentence_tokens[j:i])

                # 检查token限制
                if chunk_tokens > config.max_chunk_tokens:
                    continue

                # 计算区间内的语义凝聚度
                if i - j == 1:
                    cohesion = 1.0
                else:
                    sub_matrix = similarity_matrix[j:i, j:i]
                    triu_indices = np.triu_indices(i - j, k=1)
                    cohesion = np.mean(sub_matrix[triu_indices])

                # 计算长度适配度
                length_score = 1.0 - min(1.0, chunk_tokens / config.max_chunk_tokens) * 0.3

                # 区间得分
                interval_score = cohesion * 0.7 + length_score * 0.3

                # 更新DP
                total_score = dp[j]['score'] + interval_score
                if total_score > dp[i]['score']:
                    new_chunk = {
                        'content': chunk_text,
                        'tokens': chunk_tokens,
                        'sentences': i - j,
                        'cohesion': cohesion
                    }
                    dp[i] = {
                        'score': total_score,
                        'chunks': dp[j]['chunks'] + [new_chunk],
                        'last': j
                    }

        return dp[n]['chunks']

    def _hybrid_chunking(self, content: str, config: ChunkConfig) -> List[Dict]:
        """混合分块：结合语义和结构"""
        # 分析文档结构
        analysis = self.analyzer.analyze(content)

        chunks = []
        current_sentences = []
        current_tokens = 0

        for para_info in analysis['paragraphs']:
            # 如果是标题，强制分块
            if para_info['is_heading']:
                # 结束当前分块
                if current_sentences:
                    chunk_text = ''.join(current_sentences)
                    chunks.append({
                        'content': chunk_text,
                        'tokens': current_tokens,
                        'type': 'content_chunk',
                        'sentences': len(current_sentences)
                    })
                    current_sentences = []
                    current_tokens = 0

                # 标题作为单独分块
                chunks.append({
                    'content': para_info['text'],
                    'tokens': self.tokenizer.count_tokens(para_info['text']),
                    'type': f'heading_level_{para_info["heading_level"]}',
                    'sentences': 1,
                    'is_heading': True
                })
                continue

            # 处理段落内的句子
            for sentence in para_info['sentences']:
                sentence_tokens = self.tokenizer.count_tokens(sentence)

                # 检查是否需要开始新分块
                if current_sentences:
                    # 计算语义相似度
                    prev_sentence = current_sentences[-1]
                    similarity = self.embedder.compute_similarity(prev_sentence, sentence)

                    should_start_new = (
                            current_tokens + sentence_tokens > config.max_chunk_tokens or
                            similarity < config.similarity_threshold or
                            len(current_sentences) >= config.max_sentences_per_chunk
                    )

                    if should_start_new:
                        # 结束当前分块
                        chunk_text = ''.join(current_sentences)
                        chunks.append({
                            'content': chunk_text,
                            'tokens': current_tokens,
                            'type': 'content_chunk',
                            'sentences': len(current_sentences)
                        })
                        current_sentences = [sentence]
                        current_tokens = sentence_tokens
                    else:
                        # 继续当前分块
                        current_sentences.append(sentence)
                        current_tokens += sentence_tokens
                else:
                    # 开始新分块
                    current_sentences = [sentence]
                    current_tokens = sentence_tokens

        # 添加最后一个分块
        if current_sentences:
            chunk_text = ''.join(current_sentences)
            chunks.append({
                'content': chunk_text,
                'tokens': current_tokens,
                'type': 'content_chunk',
                'sentences': len(current_sentences)
            })

        return chunks

    def _dynamic_chunking(self, content: str, config: ChunkConfig) -> List[Dict]:
        """动态分块：自适应调整分块大小"""
        sentences = self.sentence_splitter.split_sentences(content)
        if not sentences:
            return []

        # 计算句子复杂度和长度
        sentence_complexities = []
        for sentence in sentences:
            # 复杂度基于句子长度和标点数量
            length = len(sentence)
            punct_count = sum(1 for c in sentence if c in '，。！？；：')
            complexity = length * 0.5 + punct_count * 10
            sentence_complexities.append(complexity)

        # 动态调整每个分块的目标token数
        chunks = []
        current_chunk = []
        current_tokens = 0
        current_complexity = 0

        for i, (sentence, complexity) in enumerate(zip(sentences, sentence_complexities)):
            sentence_tokens = self.tokenizer.count_tokens(sentence)

            # 动态目标token数：基于复杂度调整
            dynamic_target = config.max_chunk_tokens
            if complexity > 50:  # 复杂句子
                dynamic_target = int(config.max_chunk_tokens * 0.7)

            # 检查是否开始新分块
            if (current_tokens + sentence_tokens > dynamic_target or
                    current_complexity + complexity > 100):

                if current_chunk:
                    chunk_text = ''.join(current_chunk)
                    chunks.append({
                        'content': chunk_text,
                        'tokens': current_tokens,
                        'type': 'dynamic_chunk',
                        'sentences': len(current_chunk),
                        'avg_complexity': current_complexity / len(current_chunk) if current_chunk else 0
                    })

                current_chunk = [sentence]
                current_tokens = sentence_tokens
                current_complexity = complexity
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
                current_complexity += complexity

        # 添加最后一个分块
        if current_chunk:
            chunk_text = ''.join(current_chunk)
            chunks.append({
                'content': chunk_text,
                'tokens': current_tokens,
                'type': 'dynamic_chunk',
                'sentences': len(current_chunk),
                'avg_complexity': current_complexity / len(current_chunk) if current_chunk else 0
            })

        return chunks

    def _post_process(self, chunks: List[Dict],
                      original_content: str,
                      config: ChunkConfig) -> List[Dict]:
        """后处理分块"""
        # 1. 过滤太小的分块（合并到相邻分块）
        filtered_chunks = []
        for i, chunk in enumerate(chunks):
            if chunk['tokens'] < config.min_chunk_tokens and i > 0:
                # 合并到前一个分块
                prev_chunk = filtered_chunks[-1]
                prev_chunk['content'] += chunk['content']
                prev_chunk['tokens'] += chunk['tokens']
                prev_chunk['sentences'] += chunk.get('sentences', 1)
            else:
                filtered_chunks.append(chunk.copy())

        # 2. 添加重叠
        if config.overlap_tokens > 0:
            for i in range(1, len(filtered_chunks)):
                current = filtered_chunks[i]
                prev = filtered_chunks[i - 1]

                overlap_text = self._create_overlap(prev['content'], current['content'],
                                                    config.overlap_tokens)
                if overlap_text:
                    current['content'] = overlap_text + current['content']
                    current['tokens'] = self.tokenizer.count_tokens(current['content'])
                    current['has_overlap'] = True

        # 3. 验证内容一致性
        for chunk in filtered_chunks:
            if chunk['content'] not in original_content:
                # 查找最佳匹配
                chunk['content'] = self._find_best_match(chunk['content'], original_content)
                chunk['tokens'] = self.tokenizer.count_tokens(chunk['content'])

        return filtered_chunks

    def _create_overlap(self, prev_content: str,
                        current_content: str,
                        overlap_tokens: int) -> str:
        """创建重叠内容"""
        # 从上一个分块末尾提取句子作为重叠
        prev_sentences = self.sentence_splitter.split_sentences(prev_content)

        overlap_sentences = []
        overlap_token_count = 0

        for sentence in reversed(prev_sentences):
            sentence_tokens = self.tokenizer.count_tokens(sentence)
            if overlap_token_count + sentence_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                overlap_token_count += sentence_tokens
            else:
                break

        if overlap_sentences:
            return ''.join(overlap_sentences)
        return ""

    def _find_best_match(self, chunk_content: str, original_content: str) -> str:
        """在原始内容中查找最佳匹配"""
        # 简单实现：使用滑动窗口
        chunk_len = len(chunk_content)
        if chunk_len == 0:
            return ""

        best_match = ""
        best_score = 0

        for i in range(len(original_content) - chunk_len + 1):
            substr = original_content[i:i + chunk_len]

            # 计算匹配度
            match_count = sum(1 for a, b in zip(substr, chunk_content) if a == b)
            score = match_count / chunk_len

            if score > best_score:
                best_score = score
                best_match = substr

        return best_match if best_score > 0.8 else chunk_content

    def _add_metadata(self, chunks: List[Dict],
                      config: ChunkConfig,
                      processing_time: float) -> List[Dict[str, Any]]:
        """添加元数据"""
        final_chunks = []

        for i, chunk in enumerate(chunks):
            # 计算分块质量评分
            quality_score = self._calculate_quality_score(chunk)

            final_chunk = {
                'tokens': chunk['tokens'],
                'content': chunk['content'].strip(),
                'chunk_order_index': i,
                'chunk_type': chunk.get('type', 'unknown'),
                'metadata': {
                    'quality_score': quality_score,
                    'sentences': chunk.get('sentences', 1),
                    'has_overlap': chunk.get('has_overlap', False),
                    'avg_complexity': chunk.get('avg_complexity', 0),
                    'cohesion': chunk.get('cohesion', 0),
                    'processing_time_ms': int(processing_time * 1000 / len(chunks)),
                    'config': {
                        'max_chunk_tokens': config.max_chunk_tokens,
                        'min_chunk_tokens': config.min_chunk_tokens,
                        'overlap_tokens': config.overlap_tokens,
                        'similarity_threshold': config.similarity_threshold,
                    }
                }
            }

            final_chunks.append(final_chunk)

        return final_chunks

    def _calculate_quality_score(self, chunk: Dict) -> float:
        """计算分块质量评分"""
        score = 0.0

        # 1. 长度评分 (30%)
        token_count = chunk['tokens']
        if 200 <= token_count <= 800:
            length_score = 1.0
        else:
            length_score = max(0.0, 1.0 - abs(token_count - 500) / 1000)
        score += length_score * 0.3

        # 2. 句子数评分 (20%)
        sentence_count = chunk.get('sentences', 1)
        if 2 <= sentence_count <= 10:
            sentence_score = 1.0
        else:
            sentence_score = max(0.0, 1.0 - abs(sentence_count - 6) / 20)
        score += sentence_score * 0.2

        # 3. 语义凝聚度 (30%)
        cohesion = chunk.get('cohesion', 0.7)
        score += cohesion * 0.3

        # 4. 复杂度评分 (20%)
        complexity = chunk.get('avg_complexity', 30)
        if 20 <= complexity <= 80:
            complexity_score = 1.0
        else:
            complexity_score = max(0.0, 1.0 - abs(complexity - 50) / 100)
        score += complexity_score * 0.2

        return min(1.0, max(0.0, score))


class ChineseSemanticChunkingSystem:
    """完整的中文语义分块系统"""

    def __init__(self,
                 model_path: str = r"D:\PythonProject\models\bge-large-zh-v1.5",
                 config: Optional[ChunkConfig] = None):
        """
        初始化系统

        Args:
            model_name: BGE 模型名称
            config: 分块配置
        """
        logger.info("初始化中文语义分块系统...")

        # 初始化组件
        self.embedder = BGEChineseEmbedder(model_path)
        self.tokenizer = BGEChineseTokenizer(model_path)
        self.config = config or ChunkConfig()

        # 初始化分块器
        self.chunker = SemanticChunker(self.embedder, self.tokenizer, self.config)

        logger.info("系统初始化完成")

    def chunk_document(self,
                       document: str,
                       strategy: str = "hybrid",
                       **kwargs) -> List[Dict[str, Any]]:
        """
        分块文档

        Args:
            document: 输入文档
            strategy: 分块策略 ('semantic', 'hybrid', 'hierarchical', 'dynamic')
            **kwargs: 配置参数

        Returns:
            分块结果列表
        """
        # 验证输入
        if not document or not document.strip():
            logger.warning("输入文档为空")
            return []

        # 选择策略
        strategy_enum = ChunkingStrategy.HYBRID
        if strategy.lower() == 'semantic':
            strategy_enum = ChunkingStrategy.SEMANTIC
        elif strategy.lower() == 'hierarchical':
            strategy_enum = ChunkingStrategy.HIERARCHICAL
        elif strategy.lower() == 'dynamic':
            strategy_enum = ChunkingStrategy.DYNAMIC

        # 执行分块
        chunks = self.chunker.chunk(document, strategy_enum, **kwargs)

        return chunks

    def batch_chunk_documents(self,
                              documents: List[str],
                              strategy: str = "hybrid",
                              **kwargs) -> List[List[Dict[str, Any]]]:
        """批量分块文档"""
        results = []
        for i, doc in enumerate(documents):
            logger.info(f"处理文档 {i + 1}/{len(documents)}")
            chunks = self.chunk_document(doc, strategy, **kwargs)
            results.append(chunks)
        return results


# 使用示例和测试
def main():
    """主函数：演示如何使用系统"""
    file_path = r"D:\PythonProject\LightRAG\rag_storage\kv_store_full_docs.json"

    # 读取JSON文件
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 检查目标ID是否存在
    target_id = "doc-c06e6d924d1ab51068fb5043f25de9fb"
    if target_id in data:
        content = data[target_id].get('content', '')
        print(f"成功提取 ID: {target_id}")

    # 示例中文文档
    sample_document = content

    print("=" * 80)
    print("中文语义分块系统演示")
    print("=" * 80)

    # 初始化系统
    print("\n1. 初始化系统...")
    system = ChineseSemanticChunkingSystem(
        model_path=r"D:\PythonProject\models\bge-large-zh-v1.5",
        config=ChunkConfig(
            max_chunk_tokens=1200,
            min_chunk_tokens=150,
            overlap_tokens=50,
            similarity_threshold=0.75,
            topic_shift_threshold=0.35
        )
    )

    # 测试不同策略
    strategies = ['hybrid', 'semantic', 'hierarchical', 'dynamic']

    for strategy in strategies:
        print(f"\n{'=' * 60}")
        print(f"测试策略: {strategy}")
        print(f"{'=' * 60}")

        # 执行分块
        start_time = time.time()
        chunks = system.chunk_document(
            document=sample_document,
            strategy=strategy,
            max_chunk_tokens=800,
            overlap_tokens=50
        )
        elapsed = time.time() - start_time

        # 显示结果
        print(f"生成分块数: {len(chunks)}")
        print(f"处理时间: {elapsed:.2f}秒")
        print(f"平均每个分块: {elapsed / len(chunks) * 1000:.1f}毫秒")

        # 显示前3个分块的摘要
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n[分块 {i + 1}]")
            print(f"类型: {chunk['chunk_type']}")
            print(f"Token数: {chunk['tokens']}")
            print(f"质量评分: {chunk['metadata']['quality_score']:.2f}")
            print(f"句子数: {chunk['metadata']['sentences']}")
            preview = chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content']
            print(f"内容预览: {preview}")

        if len(chunks) > 3:
            print(f"\n... 还有 {len(chunks) - 3} 个分块未显示")

    # 统计分析
    print(f"\n{'=' * 80}")
    print("统计分析")
    print(f"{'=' * 80}")

    # 使用混合策略进行详细分析
    chunks = system.chunk_document(sample_document, strategy='hybrid')

    total_tokens = sum(chunk['tokens'] for chunk in chunks)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    avg_sentences = sum(chunk['metadata']['sentences'] for chunk in chunks) / len(chunks) if chunks else 0
    avg_quality = sum(chunk['metadata']['quality_score'] for chunk in chunks) / len(chunks) if chunks else 0

    print(f"文档总Token数: {len(system.tokenizer.encode(sample_document))}")
    print(f"分块总数: {len(chunks)}")
    print(f"平均每个分块Token数: {avg_tokens:.1f}")
    print(f"平均每个分块句子数: {avg_sentences:.1f}")
    print(f"平均质量评分: {avg_quality:.3f}")

    # 分块类型分布
    type_dist = {}
    for chunk in chunks:
        chunk_type = chunk['chunk_type']
        type_dist[chunk_type] = type_dist.get(chunk_type, 0) + 1

    print(f"\n分块类型分布:")
    for chunk_type, count in sorted(type_dist.items()):
        percentage = count / len(chunks) * 100
        print(f"  {chunk_type}: {count}个 ({percentage:.1f}%)")

    print(f"\n{'=' * 80}")
    print("演示完成")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    # 检查依赖
    try:
        import torch
        import numpy as np

        print("依赖检查通过")
        main()
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请安装以下依赖:")
        print("pip install torch transformers numpy")