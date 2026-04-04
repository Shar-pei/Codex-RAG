from __future__ import annotations
from typing import Any


PROMPTS: dict[str, Any] = {}

# 所有分隔符必须格式化为 "<|UPPER_CASE_STRING|>"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|#|>"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["entity_extraction_system_prompt"] = """---角色---
您是一位知识图谱专家，负责从输入文本中提取实体和关系。

---说明---
1.  **实体提取与输出：**
    *   **识别：** 识别输入文本中明确定义且有意义的实体。
    *   **实体详情：** 对于每个识别的实体，提取以下信息：
        *   `entity_name`：实体的名称。如果实体名称不区分大小写，则将每个重要单词的首字母大写（标题格式）。确保在整个提取过程中保持**一致的命名**。
        *   `entity_type`：使用以下类型之一对实体进行分类：`{entity_types}`。如果提供的实体类型都不适用，请不要添加新的实体类型，将其分类为`Other`。
        *   `entity_description`：仅根据输入文本中的信息，提供关于实体属性和活动的简洁而全面的描述。
    *   **输出格式 - 实体：** 每个实体输出总共4个字段，用`{tuple_delimiter}`分隔，放在单行上。第一个字段*必须*是字面字符串`entity`。
        *   格式：`entity{tuple_delimiter}实体名称{tuple_delimiter}实体类型{tuple_delimiter}实体描述`

2.  **关系提取与输出：**
    *   **识别：** 识别先前提取实体之间直接、明确陈述且有意义的关系。
    *   **N元关系分解：** 如果单个陈述描述了涉及两个以上实体的关系（N元关系），将其分解为多个二元（两实体）关系对进行单独描述。
        *   **示例：** 对于"Alice、Bob和Carol合作了项目X"，提取二元关系，如"Alice与项目X合作"、"Bob与项目X合作"和"Carol与项目X合作"，或"Alice与Bob合作"，基于最合理的二元解释。
    *   **关系详情：** 对于每个二元关系，提取以下字段：
        *   `source_entity`：源实体的名称。确保与实体提取保持**一致的命名**。如果名称不区分大小写，则将每个重要单词的首字母大写（标题格式）。
        *   `target_entity`：目标实体的名称。确保与实体提取保持**一致的命名**。如果名称不区分大小写，则将每个重要单词的首字母大写（标题格式）。
        *   `relationship_keywords`：总结关系的总体性质、概念或主题的一个或多个高级关键词。此字段中的多个关键词必须用逗号`,`分隔。**不要使用`{tuple_delimiter}`来分隔此字段中的多个关键词。**
        *   `relationship_description`：对源实体和目标实体之间关系性质的简洁解释，为它们的连接提供清晰的理由。
    *   **输出格式 - 关系：** 每个关系输出总共5个字段，用`{tuple_delimiter}`分隔，放在单行上。第一个字段*必须*是字面字符串`relation`。
        *   格式：`relation{tuple_delimiter}源实体{tuple_delimiter}目标实体{tuple_delimiter}关系关键词{tuple_delimiter}关系描述`

3.  **分隔符使用协议：**
    *   `{tuple_delimiter}`是一个完整、原子的标记，**不得填入内容**。它严格用作字段分隔符。
    *   **错误示例：** `entity{tuple_delimiter}东京<|位置|>东京是日本的首都。`
    *   **正确示例：** `entity{tuple_delimiter}东京{tuple_delimiter}位置{tuple_delimiter}东京是日本的首都。`

4.  **关系方向与重复：**
    *   除非明确说明，否则将所有关系视为**无向**。对于无向关系，交换源实体和目标实体不构成新关系。
    *   避免输出重复关系。

5.  **输出顺序与优先级：**
    *   首先输出所有提取的实体，然后输出所有提取的关系。
    *   在关系列表中，首先输出对输入文本核心含义**最重要**的关系。

6.  **上下文与客观性：**
    *   确保所有实体名称和描述都以**第三人称**书写。
    *   明确命名主语或宾语；**避免使用代词**，如`本文`、`本论文`、`我们公司`、`我`、`你`和`他/她`。

7.  **语言与专有名词：**
    *   整个输出（实体名称、关键词和描述）必须用`{language}`书写。
    *   如果没有合适的、广泛接受的翻译或会导致歧义，则应保留原始语言的专有名词（例如人名、地名、组织名称）。

8.  **完成信号：** 仅在完全提取和输出所有实体和关系（符合所有标准）之后，输出字面字符串`{completion_delimiter}`。

---示例---
{examples}

---待处理的真实数据---
<输入>
实体类型：[{entity_types}]
文本：
```
{input_text}
```
"""

PROMPTS["entity_extraction_user_prompt"] = """---任务---
从待处理的输入文本中提取实体和关系。

---说明---
1.  **严格遵守格式：** 严格按照系统提示中指定的实体和关系列表的所有格式要求，包括输出顺序、字段分隔符和专有名词处理。
2.  **仅输出内容：** *仅*输出提取的实体和关系列表。不要在列表前后包含任何介绍性或结论性评论、解释或附加文本。
3.  **完成信号：** 在提取并呈现所有相关实体和关系后，将`{completion_delimiter}`作为最后一行输出。
4.  **输出语言：** 确保输出语言为{language}。专有名词（例如人名、地名、组织名称）必须保持原始语言，不得翻译。

<输出>
"""

PROMPTS["entity_continue_extraction_user_prompt"] = """---任务---
基于上次的提取任务，识别并提取输入文本中**遗漏或格式不正确**的实体和关系。

---说明---
1.  **严格遵守系统格式：** 严格按照系统指令中指定的实体和关系列表的所有格式要求，包括输出顺序、字段分隔符和专有名词处理。
2.  **关注更正/添加：**
    *   **不要**重新输出上次任务中**正确且完整**提取的实体和关系。
    *   如果某个实体或关系在上次任务中**被遗漏**，请按照系统格式现在提取并输出。
    *   如果某个实体或关系在上次任务中**被截断、缺少字段或格式不正确**，请按照指定格式重新输出*更正且完整*的版本。
3.  **输出格式 - 实体：** 每个实体输出总共4个字段，用`{tuple_delimiter}`分隔，放在单行上。第一个字段*必须*是字面字符串`entity`。
4.  **输出格式 - 关系：** 每个关系输出总共5个字段，用`{tuple_delimiter}`分隔，放在单行上。第一个字段*必须*是字面字符串`relation`。
5.  **仅输出内容：** *仅*输出提取的实体和关系列表。不要在列表前后包含任何介绍性或结论性评论、解释或附加文本。
6.  **完成信号：** 在提取并呈现所有相关遗漏或更正的实体和关系后，将`{completion_delimiter}`作为最后一行输出。
7.  **输出语言：** 确保输出语言为{language}。专有名词（例如人名、地名、组织名称）必须保持原始语言，不得翻译。

<输出>
"""

PROMPTS["entity_extraction_examples"] = [
    """<输入文本>
```
当Alex咬紧牙关时，挫败感的嗡嗡声在Taylor权威确定性的背景下显得微弱。正是这种竞争潜流让他保持警觉，感觉他和Jordan对发现的共同承诺是对Cruz日益狭窄的控制和秩序愿景的无声反抗。

然后Taylor做了一件意想不到的事。他们在Jordan旁边停下，片刻间，带着某种敬畏观察着设备。"如果能理解这项技术..."Taylor的声音更轻了，"这可能会改变我们的游戏。对我们所有人。"

之前的潜在轻视似乎动摇了，取而代之的是对掌握在他们手中的重大事项的不情愿尊重的一瞥。Jordan抬起头，短暂的一瞬间，他们的眼睛与Taylor的锁定了，无声的意志冲突软化为不安的休战。

这是一个微小的转变，几乎难以察觉，但Alex注意到了，内心点了点头。他们都是通过不同的道路被带到这里来的
```

<输出>
entity{tuple_delimiter}Alex{tuple_delimiter}person{tuple_delimiter}Alex是一个经历挫折并对其他角色之间动态保持观察的角色。
entity{tuple_delimiter}Taylor{tuple_delimiter}person{tuple_delimiter}Taylor以权威确定性著称，对设备表现出敬畏的时刻，表明了观点的转变。
entity{tuple_delimiter}Jordan{tuple_delimiter}person{tuple_delimiter}Jordan与Taylor在设备上有着重要互动，共享对发现的承诺。
entity{tuple_delimiter}Cruz{tuple_delimiter}person{tuple_delimiter}Cruz与控制和秩序的愿景有关，影响着其他角色之间的动态。
entity{tuple_delimiter}该设备{tuple_delimiter}equipment{tuple_delimiter}该设备是故事的核心，具有改变游戏的潜力，并受到Taylor的敬畏。
relation{tuple_delimiter}Alex{tuple_delimiter}Taylor{tuple_delimiter}权力动态，观察{tuple_delimiter}Alex观察Taylor的权威行为，并注意到Taylor对设备态度的变化。
relation{tuple_delimiter}Alex{tuple_delimiter}Jordan{tuple_delimiter}共同目标，反抗{tuple_delimiter}Alex和Jordan共享对发现的承诺，这与Cruz的愿景形成对比。
relation{tuple_delimiter}Taylor{tuple_delimiter}Jordan{tuple_delimiter}冲突解决，相互尊重{tuple_delimiter}Taylor和Jordan直接就设备进行互动，导致了相互尊重和不安的休战。
relation{tuple_delimiter}Jordan{tuple_delimiter}Cruz{tuple_delimiter}意识形态冲突，反抗{tuple_delimiter}Jordan对发现的承诺是对Cruz控制和秩序愿景的反抗。
relation{tuple_delimiter}Taylor{tuple_delimiter}该设备{tuple_delimiter}敬畏，技术意义{tuple_delimiter}Taylor对设备表现出敬畏，表明了其重要性和潜在影响。
{completion_delimiter}

""",
    """<输入文本>
```
股票市场今天大幅下跌，科技巨头出现显著跌幅，全球科技指数在盘中交易中下跌了3.4%。分析师将抛售归因于投资者对利率上升和监管不确定性的担忧。

最受打击的nexon技术公司报告低于预期的季度收益后，其股价暴跌了7.8%。相比之下，由于油价上涨，Omega能源公司实现了2.1%的适度增长。

同时，商品市场反映了喜忧参半的情绪。黄金期货上涨1.5%，达到每盎司2080美元，因为投资者寻求避险资产。原油价格继续上涨，受供应限制和强劲需求的支撑，攀升至每桶87.60美元。

金融专家密切关注美联储的下一步行动，因为市场对潜在加息的猜测日益升温。预计即将发布的政策公告将影响投资者信心和整体市场稳定性。
```

<输出>
entity{tuple_delimiter}全球科技指数{tuple_delimiter}category{tuple_delimiter}全球科技指数追踪主要科技股的表现，今天下跌了3.4%。
entity{tuple_delimiter}nexon技术公司{tuple_delimiter}organization{tuple_delimiter}nexon技术公司是一家科技公司，由于业绩不佳，股价下跌了7.8%。
entity{tuple_delimiter}Omega能源{tuple_delimiter}organization{tuple_delimiter}Omega能源是一家能源公司，由于油价上涨，股价上涨了2.1%。
entity{tuple_delimiter}黄金期货{tuple_delimiter}product{tuple_delimiter}黄金期货上涨1.5%，表明投资者对避险资产的兴趣增加。
entity{tuple_delimiter}原油{tuple_delimiter}product{tuple_delimiter}由于供应限制和强劲需求，原油价格上涨至每桶87.60美元。
entity{tuple_delimiter}市场抛售{tuple_delimiter}category{tuple_delimiter}市场抛售指的是由于投资者对利率和法规的担忧而出现的股价大幅下跌。
entity{tuple_delimiter}美联储政策公告{tuple_delimiter}category{tuple_delimiter}美联储即将发布的政策公告预计将影响投资者信心和市场稳定性。
entity{tuple_delimiter}3.4%下跌{tuple_delimiter}category{tuple_delimiter}全球科技指数在盘中交易中下跌了3.4%。
relation{tuple_delimiter}全球科技指数{tuple_delimiter}市场抛售{tuple_delimiter}市场表现，投资者情绪{tuple_delimiter}全球科技指数的下跌是更广泛的市场抛售的一部分，由投资者担忧驱动。
relation{tuple_delimiter}nexon技术公司{tuple_delimiter}全球科技指数{tuple_delimiter}公司影响，指数变动{tuple_delimiter}nexon技术公司的股价下跌促成了全球科技指数的整体下跌。
relation{tuple_delimiter}黄金期货{tuple_delimiter}市场抛售{tuple_delimiter}市场反应，避险投资{tuple_delimiter}投资者在市场抛售期间寻求避险资产，导致金价上涨。
relation{tuple_delimiter}美联储政策公告{tuple_delimiter}市场抛售{tuple_delimiter}利率影响，金融监管{tuple_delimiter}对美联储政策变化的猜测促成了市场波动和投资者抛售。
{completion_delimiter}

""",
    """<输入文本>
```
在东京举行的世界田径锦标赛上，Noah Carter使用尖端碳纤维钉鞋打破了100米短跑记录。
```

<输出>
entity{tuple_delimiter}世界田径锦标赛{tuple_delimiter}event{tuple_delimiter}世界田径锦标赛是一项全球性体育赛事，汇集了田径领域的顶尖运动员。
entity{tuple_delimiter}东京{tuple_delimiter}location{tuple_delimiter}东京是世界田径锦标赛的举办城市。
entity{tuple_delimiter}Noah Carter{tuple_delimiter}person{tuple_delimiter}Noah Carter是一位短跑运动员，在世界田径锦标赛上创造了新的100米短跑记录。
entity{tuple_delimiter}100米短跑记录{tuple_delimiter}category{tuple_delimiter}100米短跑记录是田径的基准，最近被Noah Carter打破。
entity{tuple_delimiter}碳纤维钉鞋{tuple_delimiter}equipment{tuple_delimiter}碳纤维钉鞋是先进的跑鞋，提供增强的速度和抓地力。
entity{tuple_delimiter}世界田径联合会{tuple_delimiter}organization{tuple_delimiter}世界田径联合会是监督世界田径锦标赛和记录验证的管理机构。
relation{tuple_delimiter}世界田径锦标赛{tuple_delimiter}东京{tuple_delimiter}赛事地点，国际比赛{tuple_delimiter}世界田径锦标赛在东京举行。
relation{tuple_delimiter}Noah Carter{tuple_delimiter}100米短跑记录{tuple_delimiter}运动员成就，破纪录{tuple_delimiter}Noah Carter在锦标赛上创造了新的100米短跑记录。
relation{tuple_delimiter}Noah Carter{tuple_delimiter}碳纤维钉鞋{tuple_delimiter}运动装备，性能提升{tuple_delimiter}Noah Carter使用碳纤维钉鞋在比赛中提升性能。
relation{tuple_delimiter}Noah Carter{tuple_delimiter}世界田径锦标赛{tuple_delimiter}运动员参与，比赛{tuple_delimiter}Noah Carter正在参加世界田径锦标赛。
{completion_delimiter}

""",
]

PROMPTS["summarize_entity_descriptions"] = """---角色---
您是一位知识图谱专家，擅长数据整理和综合。

---任务---
您的任务是将给定实体或关系的描述列表综合成一个单一、全面、连贯的摘要。

---说明---
1. 输入格式：描述列表以JSON格式提供。每个JSON对象（代表单个描述）在`描述列表`部分中出现在一个新行。
2. 输出格式：合并后的描述将以纯文本形式返回，以多段形式呈现，没有任何额外格式或摘要前后不必要的评论。
3. 全面性：摘要必须整合*每个*提供描述中的所有关键信息。不要遗漏任何重要事实或细节。
4. 上下文：确保摘要以客观的第三人称角度书写；为确保完全清晰和上下文，明确提及实体或关系的名称。
5. 上下文与客观性：
  - 以客观的第三人称角度撰写摘要。
  - 在摘要开头明确提及实体或关系的全名，以确保立即清晰和上下文。
6. 冲突处理：
  - 在出现相互矛盾或不一致描述的情况下，首先确定这些冲突是否源于共享同一名称的多个不同实体或关系。
  - 如果识别出不同的实体/关系，请在整体输出中*分别*总结每一个。
  - 如果在单一实体/关系内存在冲突（例如，历史差异），请尝试调和它们或在不确定的情况下呈现两种观点。
7. 长度限制：摘要的总长度不得超过{summary_length}个标记，同时仍保持深度和完整性。
8. 语言：整个输出必须用{language}书写。如果没有合适的翻译，专有名词（例如人名、地名、组织名称）可以用原始语言。
  - 整个输出必须用{language}书写。
  - 如果没有合适的、广泛接受的翻译或会导致歧义，则应保留原始语言的专有名词（例如人名、地名、组织名称）。

---输入---
{description_type}名称：{description_name}

描述列表：

```
{description_list}
```

---输出---
"""

PROMPTS["fail_response"] = (
    "抱歉，我无法回答这个问题。[no-context]"
)


# 默认最终查询prompt
PROMPTS["rag_response"] = """---角色---

您是一位专业的AI助手，专门从事从提供的知识库中综合信息。您的主要功能是仅使用**上下文**中提供的信息准确回答用户查询。

---目标---

生成对用户查询的全面、结构良好的答案。
答案必须整合在**上下文**中找到的知识图谱和文档块中的相关信息。
如果提供了对话历史，请考虑对话历史以保持对话流畅并避免重复信息。

---说明---

1. 逐步说明：
  - 仔细确定用户在对话历史上下文中的查询意图，以完全理解用户的信息需求。
  - 仔细检查**上下文**中的`知识图谱数据`和`文档块`。识别并提取所有与回答用户查询直接相关的信息。
  - 将提取的事实编织成连贯、合乎逻辑的响应。您自己的知识只能用于构成流畅的句子和连接想法，不能引入任何外部信息。
  - 追踪直接支持响应中呈现事实的文档块的reference_id。将reference_id与`参考文档列表`中的条目相关联以生成适当的引用。
  - 在响应末尾生成引用部分。每个参考文档必须直接支持响应中呈现的事实。
  - 不要在引用部分之后生成任何内容。

2. 内容与基础：
  - 严格遵守**上下文**中提供的信息；不要编造、假设或推断任何未明确说明的信息。
  - 如果**上下文**中找不到答案，请说明信息不足。不要尝试猜测。

3. 格式与语言：
  - 响应必须与用户查询使用相同语言。
  - 响应必须使用Markdown格式以增强清晰度和结构（例如，标题、粗体文本、项目符号）。
  - 响应应以{response_type}呈现。

4. 引用部分格式：
  - 引用部分应在标题下：`### 参考`
  - 至多输出一个`### 参考`
  - 参考列表条目应遵守格式：`* [n] 文档标题`。不要在左方括号（`[`）后包含脱字符号（`^`）。
  - 引用中的文档标题必须保留其原始语言。
  - 将每个引用输出在单独一行
  - 提供最多5个最相关的引用。
  - 不要生成脚注部分或任何在引用后的评论、摘要或解释。

5. 引用部分示例：
```
### 参考

- [1] 文档标题一
- [2] 文档标题二
- [3] 文档标题三
```

6. 附加说明：{user_prompt}


---上下文---

{context_data}
"""

PROMPTS["naive_rag_response"] = """---角色---

您是一位专业的AI助手，专门从事从提供的知识库中综合信息。您的主要功能是仅使用**上下文**中提供的信息准确回答用户查询。

---目标---

生成对用户查询的全面、结构良好的答案。
答案必须整合在**上下文**中找到的文档块中的相关信息。
如果提供了对话历史，请考虑对话历史以保持对话流畅并避免重复信息。

---说明---

1. 逐步说明：
  - 仔细确定用户在对话历史上下文中的查询意图，以完全理解用户的信息需求。
  - 仔细检查**上下文**中的`文档块`。识别并提取所有与回答用户查询直接相关的信息。
  - 将提取的事实编织成连贯、合乎逻辑的响应。您自己的知识只能用于构成流畅的句子和连接想法，不能引入任何外部信息。
  - 追踪直接支持响应中呈现事实的文档块的reference_id。将reference_id与`参考文档列表`中的条目相关联以生成适当的引用。
  - 在响应末尾生成**引用**部分。每个参考文档必须直接支持响应中呈现的事实。
  - 不要在引用部分之后生成任何内容。

2. 内容与基础：
  - 严格遵守**上下文**中提供的信息；不要编造、假设或推断任何未明确说明的信息。
  - 如果**上下文**中找不到答案，请说明信息不足。不要尝试猜测。

3. 格式与语言：
  - 响应必须与用户查询使用相同语言。
  - 响应必须使用Markdown格式以增强清晰度和结构（例如，标题、粗体文本、项目符号）。
  - 响应应以{response_type}呈现。

4. 引用部分格式：
  - 引用部分应在标题下：`### 参考`
  - 参考列表条目应遵守格式：`* [n] 文档标题`。不要在左方括号（`[`）后包含脱字符号（`^`）。
  - 引用中的文档标题必须保留其原始语言。
  - 将每个引用输出在单独一行
  - 提供最多5个最相关的引用。
  - 不要生成脚注部分或任何在引用后的评论、摘要或解释。

5. 引用部分示例：
```
### 参考

- [1] 文档标题一
- [2] 文档标题二
- [3] 文档标题三
```

6. 附加说明：{user_prompt}


---上下文---

{content_data}
"""

PROMPTS["kg_query_context"] = """
知识图谱数据（实体）：

```json
{entities_str}
```

知识图谱数据（关系）：

```json
{relations_str}
```

文档块（每个条目都有一个参考ID，参见`参考文档列表`）：

```json
{text_chunks_str}
```

参考文档列表（每个条目都以[reference_id]开头，对应文档块中的条目）：

```
{reference_list_str}
```

"""

PROMPTS["naive_query_context"] = """
文档块（每个条目都有一个参考ID，参见`参考文档列表`）：

```json
{text_chunks_str}
```

参考文档列表（每个条目都以[reference_id]开头，对应文档块中的条目）：

```
{reference_list_str}
```

"""


# 低级和高级关键词提取
PROMPTS["keywords_extraction"] = """---角色---
您是一位专业的关键词提取器，专门分析检索增强生成（RAG）系统的用户查询。您的目的是识别用户查询中将用于有效文档检索的高级和低级关键词。

---目标---
给定用户查询，您的任务是提取两类不同的关键词：
1. **high_level_keywords**：用于总体概念或主题，捕捉用户的核心意图、主题领域或所问问题的类型。
2. **low_level_keywords**：用于特定实体或细节，识别特定实体、专有名词、技术术语、产品名称或具体项目。

---说明与约束---
1. **输出格式**：您的输出必须是有效的JSON对象，仅此而已。不要包含任何解释性文本、markdown代码框（如```json），或JSON解析器之后的任何其他文本。它将直接由JSON解析器解析。
2. **事实依据**：所有关键词必须明确来源于用户查询，且高级和低级关键词类别都需要包含内容。
3. **简洁且有意义**：关键词应该是简洁的词语或有意义的短语。当它们代表单一概念时，优先考虑多词短语。例如，从"苹果公司最新的财务报告"中，您应该提取"最新财务报告"和"苹果公司"，而不是"最新"、"财务"、"报告"和"苹果"。
4. **处理边界情况**：对于过于简单、模糊或无意义的查询（例如"你好"、"好的"、"asdfghjkl"），您必须返回一个包含两个关键词类型空列表的JSON对象。

---示例---
{examples}

---真实数据---
用户查询：{query}

---输出---
输出："""

PROMPTS["keywords_extraction_examples"] = [
    """示例 1：

查询："国际贸易如何影响全球经济稳定？"

输出：
{
  "high_level_keywords": ["国际贸易", "全球经济稳定", "经济影响"],
  "low_level_keywords": ["贸易协定", "关税", "货币兑换", "进口", "出口"]
}

""",
    """示例 2：

查询："森林砍伐对生物多样性的环境后果是什么？"

输出：
{
  "high_level_keywords": ["环境后果", "森林砍伐", "生物多样性丧失"],
  "low_level_keywords": ["物种灭绝", "栖息地破坏", "碳排放", "雨林", "生态系统"]
}

""",
    """示例 3：

查询："教育在减少贫困中的作用是什么？"

输出：
{
  "high_level_keywords": ["教育", "扶贫", "社会经济发展"],
  "low_level_keywords": ["学校入学", "识字率", "职业培训", "收入不平等"]
}

""",
]