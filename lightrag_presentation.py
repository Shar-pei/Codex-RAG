from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

def create_lightrag_presentation():
    # Create a new presentation
    prs = Presentation()

    # Set slide dimensions (16:9 aspect ratio)
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    # Slide 1: Cover Page
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Add title
    title_box = slide.shapes.add_textbox(Inches(2), Inches(1.5), Inches(9), Inches(1.5))
    title_frame = title_box.text_frame
    title_frame.clear()
    p = title_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    title = p.add_run()
    title.text = "LightRAG: Simple and Fast Retrieval-Augmented Generation"
    title.font.size = Pt(36)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)

    # Add subtitle
    subtitle_box = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(9), Inches(1))
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.clear()
    p = subtitle_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    subtitle = p.add_run()
    subtitle.text = "高效的知识图谱增强检索系统"
    subtitle.font.size = Pt(24)
    subtitle.font.color.rgb = RGBColor(100, 100, 100)

    # Add logo placeholder (if available)
    try:
        slide.shapes.add_picture("assets/logo.png", Inches(5.5), Inches(4), Inches(2), Inches(2))
    except:
        # If logo is not available, add a text placeholder
        logo_box = slide.shapes.add_textbox(Inches(5.5), Inches(4), Inches(2), Inches(2))
        logo_frame = logo_box.text_frame
        p = logo_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "LOGO"
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(200, 200, 200)

    # Add version info
    version_box = slide.shapes.add_textbox(Inches(5), Inches(6.5), Inches(4), Inches(0.5))
    version_frame = version_box.text_frame
    version_frame.clear()
    p = version_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    version = p.add_run()
    version.text = f"Version: 1.4.9.9 | Created on {os.getcwd()}"
    version.font.size = Pt(12)
    version.font.color.rgb = RGBColor(150, 150, 150)

    # Slide 2: Project Overview
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "LightRAG 项目概述"

    content.text = "LightRAG是一个简单而快速的检索增强生成（Retrieval-Augmented Generation）系统，旨在高效地存储和检索知识。\n\n主要特点：\n• 基于知识图谱的检索增强\n• 支持多种存储后端（JSON、PostgreSQL、MongoDB等）\n• 提供多种查询模式（本地、全局、混合）\n• 高效的向量检索和图检索结合\n• 支持Web UI和API接口"

    # Slide 3: Core Features
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "LightRAG 核心特性"

    content.text = "1. 知识图谱增强：\n   • 自动从文档中提取实体和关系\n   • 构建知识图谱以支持复杂查询\n\n2. 多层检索：\n   • 结合向量检索和图检索\n   • 支持本地、全局和混合查询模式\n\n3. 高性能：\n   • 针对大规模数据集优化\n   • 支持并发处理\n\n4. 灵活配置：\n   • 支持多种LLM和嵌入模型\n   • 可配置的存储后端\n\n5. 易于使用：\n   • 简单的API接口\n   • Web UI支持"

    # Slide 4: Architecture and Workflow
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "LightRAG 架构和工作流程"

    content.text = "系统架构：\n• 文档存储层：存储原始文档和分块\n• 向量存储层：存储文本块的嵌入向量\n• 图存储层：存储实体和关系的知识图谱\n• 缓存层：缓存LLM响应和检索结果\n\n工作流程：\n1. 索引阶段：\n   • 文档分块\n   • 实体关系提取\n   • 向量嵌入\n   • 构建知识图谱\n\n2. 查询阶段：\n   • 解析用户查询\n   • 执行多层检索\n   • 生成响应"

    # Slide 5: Installation and Usage
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "安装和使用方法"

    content.text = "安装方法：\n\n1. 使用pip安装：\n   pip install lightrag-hku\n\n2. 使用uv安装（推荐）：\n   uv pip install lightrag-hku\n\n3. 从源码安装：\n   git clone https://github.com/HKUDS/LightRAG.git\n   cd LightRAG\n   pip install -e .\n\n基本使用示例：\n\nimport asyncio\nfrom lightrag import LightRAG, QueryParam\n\nasync def main():\n    rag = LightRAG(working_dir=\"./rag_storage\")\n    await rag.initialize_storages()\n    await rag.ainsert(\"Your text here\")\n    result = await rag.aquery(\"Your question?\")\n    print(result)\n\nasyncio.run(main())"

    # Slide 6: Technical Requirements and Configuration
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "技术要求和配置"

    content.text = "LLM要求：\n• 至少320亿参数的模型\n• 上下文长度至少32KB（推荐64KB）\n• 推荐使用如GPT-4、Claude-3或类似能力的模型\n\n嵌入模型：\n• 推荐使用高性能嵌入模型\n• 如：BAAI/bge-m3 或 text-embedding-3-large\n• 必须在索引前确定，查询时使用相同模型\n\n重排序模型（Reranker）：\n• 可显著提升检索性能\n• 推荐：BAAI/bge-reranker-v2-m3\n\n存储配置：\n• 支持多种存储后端\n• JSON、PostgreSQL、MongoDB、Neo4j等\n• 可根据需求选择合适的存储方案"

    # Slide 7: Query Modes and Parameters
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "查询模式和参数"

    content.text = "查询模式：\n• local：关注上下文相关的信息\n• global：利用全局知识\n• hybrid：结合本地和全局检索\n• naive：基本搜索，无高级技术\n• mix：集成知识图谱和向量检索\n\n主要参数：\n• mode：指定检索模式\n• only_need_context：仅返回检索上下文\n• response_type：定义响应格式\n• stream：启用流式输出\n• top_k：检索的顶级项目数\n• max_tokens：最大token数限制\n\n示例：\nrag.aquery(\"问题\", param=QueryParam(mode=\"hybrid\"))"

    # Slide 8: Summary and Resources
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title, content = slide.shapes.title, slide.placeholders[1]
    title.text = "总结和资源链接"

    content.text = "LightRAG优势：\n• 高效的RAG系统，结合向量和图检索\n• 易于集成和使用\n• 支持多种模型和存储后端\n• 活跃的社区支持\n\n项目资源：\n• GitHub: https://github.com/HKUDS/LightRAG\n• 论文: https://arxiv.org/abs/2410.05779\n• 文档: https://github.com/HKUDS/LightRAG\n• Discord: https://discord.gg/yF2MmDJyGJ\n\n使用场景：\n• 知识库问答系统\n• 文档分析和检索\n• 企业知识管理\n• 学术研究和教育"

    # Save the presentation
    prs.save("LightRAG_演示文稿.pptx")
    print("LightRAG演示文稿已创建成功！")

if __name__ == "__main__":
    create_lightrag_presentation()