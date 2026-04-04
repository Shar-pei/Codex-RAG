# 使用自定义语义分块方法

本项目现在支持使用基于BGE中文嵌入模型的语义分块方法，以替代原有的基于token的简单分块方法。

## 语义分块的优势

- **语义连贯性**：分块时考虑文本的语义内容，而不是简单的token数量
- **上下文保持**：保持句子和段落的语义完整性
- **智能边界**：在语义相关性较低的地方进行分块
- **中文优化**：专门针对中文文本进行优化

## 如何使用语义分块

### 方法1：默认使用语义分块（推荐）

在最新版本中，LightRAG已默认使用语义分块方法，无需额外配置。

### 方法2：在初始化LightRAG时指定

```python
from lightrag import LightRAG
from lightrag.operate import semantic_chunking_by_token_size

# 创建LightRAG实例，默认使用语义分块
rag = LightRAG(
    # ... 其他参数
    chunking_func=semantic_chunking_by_token_size,
    # ... 其他参数
)

# 现在所有文本分块都将使用语义分块方法
rag.insert("你的文档内容...")
```

### 方法3：直接使用语义分块函数

```python
from lightrag.operate import semantic_chunking_by_token_size
from transformers import AutoTokenizer

# 加载tokenizer
tokenizer = AutoTokenizer.from_pretrained(r"D:\PythonProject\models\bge-large-zh-v1.5")

# 使用语义分块
content = "你的文档内容..."
chunks = semantic_chunking_by_token_size(
    tokenizer=tokenizer,
    content=content,
    split_by_character=None,           # 分割字符（默认为None）
    split_by_character_only=False,     # 仅按字符分割（默认为False）
    chunk_token_size=1000,            # 最大块大小
    chunk_overlap_token_size=100,     # 重叠大小
    embedding_func=None               # 嵌入函数（可选）
)

for chunk in chunks:
    print(f"Token数: {chunk['tokens']}")
    print(f"内容: {chunk['content'][:100]}...")
    print(f"顺序: {chunk['chunk_order_index']}")
    print("---")
```

### 方法4：回退到原有分块方法

如果需要使用原有的基于token的简单分块方法：

```python
from lightrag import LightRAG
from lightrag.operate import chunking_by_token_size

# 创建LightRAG实例，使用原有分块方法
rag = LightRAG(
    # ... 其他参数
    chunking_func=chunking_by_token_size,
    # ... 其他参数
)
```

## 注意事项

1. **模型依赖**：语义分块需要BGE中文嵌入模型，请确保模型文件位于 `D:\PythonProject\models\bge-large-zh-v1.5`
2. **性能考虑**：语义分块比简单token分块更耗时，但质量更高
3. **兼容性**：原有的`chunking_by_token_size`函数仍然可用，以保持向后兼容性

## 配置参数

- `tokenizer`: 用于tokenization的tokenizer实例
- `content`: 要分块的文本内容
- `split_by_character`: 分割字符（默认为None）
- `split_by_character_only`: 是否仅按字符分割（默认为False）
- `chunk_token_size`: 最大块的token数量
- `chunk_overlap_token_size`: 块之间的重叠token数量
- `embedding_func`: 嵌入函数（可选参数）