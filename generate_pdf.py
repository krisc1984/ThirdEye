#!/usr/bin/env python3
"""Generate PDF summary of SkillGraph paper using reportlab."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Try to register Chinese font
try:
    font_paths = [
        "C:\\Windows\\Fonts\\simhei.ttf",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simsun.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            pdfmetrics.registerFont(TTFont('ChineseFont', fp))
            print(f"Registered font: {fp}")
            break
    else:
        print("No Chinese font found, using default")
except Exception as e:
    print(f"Font registration error: {e}")

def create_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='MainTitle', parent=styles['Title'], fontSize=24,
        spaceAfter=30, alignment=TA_CENTER, textColor=HexColor('#1a1a2e'),
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle', parent=styles['Heading1'], fontSize=16,
        spaceBefore=20, spaceAfter=12, textColor=HexColor('#16213e'),
        borderWidth=1, borderColor=HexColor('#0f3460'), borderPadding=5,
    ))
    styles.add(ParagraphStyle(
        name='SubSectionTitle', parent=styles['Heading2'], fontSize=13,
        spaceBefore=15, spaceAfter=8, textColor=HexColor('#0f3460'),
    ))
    styles.add(ParagraphStyle(
        name='Body', parent=styles['Normal'], fontSize=11,
        spaceAfter=8, alignment=TA_JUSTIFY, leading=16,
    ))
    styles.add(ParagraphStyle(
        name='CodeBlock', parent=styles['Normal'], fontSize=10,
        fontName='Courier', leftIndent=20, spaceAfter=10,
        backColor=HexColor('#f5f5f5'), borderWidth=1,
        borderColor=HexColor('#ddd'), borderPadding=8,
    ))
    styles.add(ParagraphStyle(
        name='QuoteBlock', parent=styles['Normal'], fontSize=11,
        leftIndent=30, rightIndent=30, spaceBefore=10, spaceAfter=10,
        textColor=HexColor('#555'), borderWidth=2,
        borderColor=HexColor('#0f3460'), borderPadding=10,
    ))
    return styles

def create_table(data, col_widths=None):
    table = Table(data, colWidths=col_widths)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0f3460')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f9f9f9')),
        ('TEXTCOLOR', (0, 1), (-1, -1), black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#ccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0f0f0')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ])
    table.setStyle(style)
    return table
def build_pdf():
    output_path = "F:\\codebaby\\ThirdEye\\SkillGraph_Paper_Summary.pdf"
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )
    styles = create_styles()
    story = []
    
    # Title
    story.append(Paragraph("SkillGraph: 多模态图拓扑的自演化多智能体协作", styles['MainTitle']))
    story.append(Spacer(1, 0.3*inch))
    
    # Paper Info
    info_data = [
        ['论文基本信息', ''],
        ['标题', 'SkillGraph: Self-Evolving Multi-Agent Collaboration with Multimodal Graph Topology'],
        ['作者', 'Zheng Nie¹, Ruolin Shen², Xinlei Yu¹, Bo Yin¹, Jiangning Zhang³, Xiaobin Hu¹'],
        ['机构', '¹新加坡国立大学, ²慕尼黑工业大学, ³浙江大学'],
        ['arXiv', 'https://arxiv.org/abs/2604.17503v1'],
        ['日期', '2026年4月19日'],
        ['代码', 'https://github.com/niez233/skillgraph'],
    ]
    story.append(create_table(info_data, col_widths=[2*inch, 4.5*inch]))
    story.append(Spacer(1, 0.3*inch))
    
    # Section 1
    story.append(Paragraph("一、研究背景与问题", styles['SectionTitle']))
    story.append(Paragraph("1.1 视觉多智能体系统(VMAS)的兴起", styles['SubSectionTitle']))
    story.append(Paragraph(
        "随着视觉语言模型(VLM)的发展，研究正从单智能体范式转向<b>视觉多智能体系统(VMAS)</b>，以利用集体智能解决复杂的多步骤多模态任务。",
        styles['BodyText']))
    
    story.append(Paragraph("1.2 现有系统的两大瓶颈", styles['SubSectionTitle']))
    bottleneck_data = [
        ['问题', '描述', '后果'],
        ['固定拓扑', '通信拓扑在推理前固定，对视觉内容和查询上下文"失明"', '无法根据任务需求动态调整协作结构'],
        ['静态能力', '智能体推理能力在部署期间保持静态', '缺乏针对特定查询的专业化动机'],
    ]
    story.append(create_table(bottleneck_data, col_widths=[1.2*inch, 2.5*inch, 2.3*inch]))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "这两个问题相互强化：刚性拓扑无法利用更丰富的智能体专业知识，而静态智能体缺乏演化动力。",
        styles['BodyText']))
    
    story.append(Paragraph("1.3 根本原因", styles['SubSectionTitle']))
    story.append(Paragraph(
        "当前架构存在<b>系统性解耦</b>：任务内容、智能体技能能力和通信拓扑三者分离。最优协作图应该是查询的多模态语义和智能体活跃技能的动态函数，而非静态模板。",
        styles['BodyText']))
    
    story.append(PageBreak())
    
    # Section 2
    story.append(Paragraph("二、核心贡献", styles['SectionTitle']))
    story.append(Paragraph("2.1 三大创新点", styles['SubSectionTitle']))
    contributions_data = [
        ['贡献', '核心思想'],
        ['技能条件化智能体', '为每个智能体配备从分层技能库中动态检索的技能，将活跃技能编码为节点特征'],
        ['MMGT拓扑设计', '多模态图Transformer联合建模视觉token、问题语义和角色先验，预测查询条件的有向拓扑'],
        ['自演化技能库', '技能设计师诊断反复失败，修改或创建技能，并将更新反馈回MMGT，形成闭环共演化'],
    ]
    story.append(create_table(contributions_data, col_widths=[1.8*inch, 4.7*inch]))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("2.2 关键突破", styles['SubSectionTitle']))
    story.append(Paragraph(
        "<b>首次实现技能演化与拓扑设计的双向耦合</b>，使智能体能力和通信结构相互强化。",
        styles['QuoteBlock']))
    
    story.append(PageBreak())
    # Section 3
    story.append(Paragraph("三、方法详解", styles['SectionTitle']))
    story.append(Paragraph("3.1 整体框架", styles['SubSectionTitle']))
    story.append(Paragraph("SkillGraph框架包含三个耦合阶段：", styles['BodyText']))
    
    framework_data = [
        ['阶段', '内容'],
        ['1. 构建阶段(Construct)', '智能体从技能库动态检索技能；组装多模态节点特征'],
        ['2. 设计阶段(Design)', 'MMGT联合编码图像内容和查询语义；预测查询条件的通信拓扑 G_com'],
        ['3. 演化阶段(Evolve)', '技能设计师从失败经验合成新技能；更新反馈回MMGT，形成闭环共演化'],
    ]
    story.append(create_table(framework_data, col_widths=[2*inch, 4.5*inch]))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("3.2 技能表示", styles['SubSectionTitle']))
    story.append(Paragraph("每个技能是一个结构化元组：s = (c_trig, d_strat, π, F, ν)", styles['CodeBlock']))
    
    skill_fields = [
        ['字段', '含义'],
        ['c_trig', '技能适用的视觉子任务触发条件'],
        ['d_strat', '逐步推理指令'],
        ['π', '运行准确率估计 (n_succ / n_use)'],
        ['F', '有界失败缓冲区'],
        ['ν', '版本计数器'],
    ]
    story.append(create_table(skill_fields, col_widths=[1*inch, 5.5*inch]))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("3.3 MMGT多模态图Transformer", styles['SubSectionTitle']))
    story.append(Paragraph("MMGT是一个五阶段编码器，包含以下组件：", styles['BodyText']))
    
    mmgt_components = [
        ['组件', '功能描述'],
        ['多模态查询编码器', '使用冻结CLIP编码器提取图像patch tokens；句子编码器编码问题文本；通过交叉注意力融合'],
        ['每智能体选择性图像注意力', '每个智能体独立关注与其分配技能相关的图像区域；通过门控机制学习上下文融合程度'],
        ['带角色先验偏置的图Transformer', '堆叠L个交替的GTL和GRNL；GTL执行全对自注意力，注意力分数通过角色先验偏置调制'],
        ['全局中继节点双向交互', '将集体智能体状态聚合到全局中继节点；将更新的全局任务上下文广播回每个智能体'],
        ['边logit预测', '使用方向感知双线性预测器计算成对边logit；支持有向通信'],
    ]
    story.append(create_table(mmgt_components, col_widths=[2*inch, 4.5*inch]))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("3.4 自适应技能演化", styles['SubSectionTitle']))
    story.append(Paragraph("<b>技能检索</b>", styles['BodyText']))
    story.append(Paragraph(
        "推理时，对所有智能体执行一次语义检索。每个技能预编码为其触发条件和策略描述的拼接句子嵌入。",
        styles['BodyText']))
    story.append(Paragraph("<b>失败累积</b>", styles['BodyText']))
    story.append(Paragraph(
        "每次查询后，将正确性结果归因于每个参与智能体的活跃技能。对错误预测，用LLM生成简洁的诊断课程。将每次失败存储为结构化记录并附加到技能的失败缓冲区。",
        styles['BodyText']))
    story.append(Paragraph("<b>技能演化</b>", styles['BodyText']))
    story.append(Paragraph(
        "每K个训练迭代，技能设计师识别困难技能（失败缓冲区大小≥τ_f），执行两种操作：",
        styles['BodyText']))
    
    evolution_ops = [
        ['操作', '触发条件', '动作'],
        ['修改', '失败模式表明策略或触发条件不精确', '修订d_strat和c_trig，递增ν，重置失败缓冲区'],
        ['创建', '失败模式暴露现有技能无法充分覆盖的视觉推理子任务', '合成新技能s_new并添加到技能库'],
    ]
    story.append(create_table(evolution_ops, col_widths=[1*inch, 2.5*inch, 3*inch]))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("3.5 共演化闭环", styles['SubSectionTitle']))
    evolution_loop = [
        ['方向', '机制'],
        ['技能库 → MMGT', '技能修改/创建 → 嵌入缓存重建 → 节点特征更新 → MMGT注意力模式隐式更新（无需参数梯度步骤）'],
        ['MMGT → 技能库', '通信拓扑决定哪些智能体协作 → 塑造哪些技能在哪些视觉子任务上被使用 → 哪些失败记录累积 → 更好的拓扑将查询导向更合适的智能体 → 更丰富的失败归因和更快的技能改进'],
    ]
    story.append(create_table(evolution_loop, col_widths=[1.5*inch, 5*inch]))
    
    story.append(PageBreak())
    # Section 4
    story.append(Paragraph("四、实验与结果", styles['SectionTitle']))
    story.append(Paragraph("4.1 实验设置", styles['SubSectionTitle']))
    exp_data = [
        ['维度', '内容'],
        ['基准', '4个基准测试'],
        ['MAS结构', '5种常见多智能体结构'],
        ['基础模型', '4个VLM骨干网络'],
    ]
    story.append(create_table(exp_data, col_widths=[1.5*inch, 4.5*inch]))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("4.2 主要发现", styles['SubSectionTitle']))
    story.append(Paragraph("• SkillGraph在四个基准上取得<b>一致改进</b>", styles['BodyText']))
    story.append(Paragraph("• 优于固定拓扑和静态技能基线", styles['BodyText']))
    story.append(Paragraph("• 代码已开源", styles['BodyText']))
    
    story.append(PageBreak())
    
    # Section 5
    story.append(Paragraph("五、相关工作对比", styles['SectionTitle']))
    story.append(Paragraph("5.1 多智能体系统作为图", styles['SubSectionTitle']))
    mas_data = [
        ['方法', '拓扑类型', '视觉感知'],
        ['早期方法 (DyLAN, DSPy等)', '静态/半动态', '❌ 仅文本'],
        ['可学习拓扑 (GPTSwarm, G-Designer, MASS)', '动态优化', '❌ 仅文本'],
        ['SkillGraph', '动态查询条件', '✅ 多模态'],
    ]
    story.append(create_table(mas_data, col_widths=[2.8*inch, 1.5*inch, 1.7*inch]))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("5.2 技能库与自改进智能体", styles['SubSectionTitle']))
    skill_data = [
        ['方面', '现有工作', 'SkillGraph'],
        ['技能更新', '仅响应任务结果', '与拓扑预测双向耦合'],
        ['视觉特征作用', '不在检索/演化中', '核心输入'],
        ['结构-知识关系', '解耦', '首次实现相互强化'],
    ]
    story.append(create_table(skill_data, col_widths=[1.5*inch, 2.5*inch, 2*inch]))
    
    story.append(PageBreak())
    
    # Section 6
    story.append(Paragraph("六、总结与展望", styles['SectionTitle']))
    story.append(Paragraph("6.1 核心思想", styles['SubSectionTitle']))
    story.append(Paragraph(
        "SkillGraph通过<b>共演化闭环</b>解决VMAS的结构和认知刚性问题：",
        styles['BodyText']))
    story.append(Paragraph("• MMGT根据多模态查询动态预测协作拓扑", styles['BodyText']))
    story.append(Paragraph("• 技能设计师从失败经验中持续演化技能库", styles['BodyText']))
    story.append(Paragraph("• 两者相互反馈，使结构和知识持续增强", styles['BodyText']))
    
    story.append(Paragraph("6.2 创新意义", styles['SubSectionTitle']))
    story.append(Paragraph(
        "这是<b>多模态微调中首次实现技能演化与拓扑设计的双向耦合机制</b>，超越了仅使用初始种子技能的先前工作。",
        styles['QuoteBlock']))
    
    story.append(Paragraph("6.3 未来方向", styles['SubSectionTitle']))
    story.append(Paragraph("论文在结论部分提到局限性和未来工作，包括：", styles['BodyText']))
    story.append(Paragraph("• 扩展至更多模态", styles['BodyText']))
    story.append(Paragraph("• 提升技能演化的可解释性", styles['BodyText']))
    story.append(Paragraph("• 在更复杂的真实世界任务中验证", styles['BodyText']))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "<i>摘要整理自 arXiv:2604.17503v1 [cs.AI]</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9,
                       textColor=HexColor('#888'), alignment=TA_CENTER)))
    
    doc.build(story)
    print(f"PDF generated successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    build_pdf()