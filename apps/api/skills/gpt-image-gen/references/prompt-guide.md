# GPT-Image-2 Prompt Engineering Guide

> 完整的 Prompt 写作参考。使用本 skill 时，根据用户需求场景查阅对应章节。

---

## 目录

- [一、核心能力速查](#一核心能力速查)
- [二、5 大铁律](#二5-大铁律)
- [三、Prompt 结构公式](#三prompt-结构公式)
- [四、Style 标签速查](#四style-标签速查)
- [五、场景模板](#五场景模板)
- [六、进阶技巧](#六进阶技巧)
- [七、常见陷阱](#七常见陷阱)
- [八、尺寸速查](#八尺寸速查)
- [九、执行流程](#九执行流程)
- [十、混合场景](#十混合场景)

---

## 一、核心能力速查

| 能力 | 说明 | Prompt 建议 |
|------|------|------------|
| 文字渲染 | 拉丁/中/日/韩/阿拉伯文 ≥95% | 关键文字 1-5 词，英文引号包裹 |
| 多元素构图 | 单图稳定承载 150+ 元素 | 用编号或列表分组 |
| 人脸一致性 | persistent embedding 跨图保持 | 固定描述年龄/种族/特征/服饰 |
| 物理材质 | 金属反射、湿地、玻璃折射正确 | 明确提及材质名和光源 |
| 编辑模式 | 原图 + edit 精确局部调整 | "preserve everything else" 锁定 |
| 世界知识 | 内置推理，理解真实事件/场景 | 可隐含上下文 |
| 4K 输出 | 原生 4K + 自定义尺寸 | 超出像素预算自动缩放 |

---

## 二、5 大铁律

### 铁律 1：主题前置
核心主体放 prompt 开头。模型对前 30% 文字赋予最高权重。

### 铁律 2：结构化场景
顺序：**场景 → 主体 + 动作 → 视觉风格/介质 → 镜头参数 → 光线 → 构图 → 约束**

### 铁律 3：文字用英文引号
所有要出现在图片中的文字用 `"..."` 包裹。文字渲染成功率从 70% → 95%+。

### 铁律 4：明确镜头与光线
指定具体参数：焦距（24mm/35mm/50mm/85mm/100mm macro）、光圈（f/1.4/f/2/f/4）、角度（eye-level/low-angle/bird's-eye）、色温（3200K warm/5600K daylight）。

### 铁律 5：编辑时分离"变与不变"
修改图片时，明确分为：`Change: ...` / `Preserve: ...`。每次编辑都要重复不变量清单。

---

## 三、Prompt 结构公式

### 通用结构（每次必用）

```
[场景描述，1-2句]
[主体描述 + 动作/状态，2-3句]
[视觉风格 / 介质，1句]
[镜头参数：焦距 + 光圈 + 角度，1句]
[光线描述：方向 + 色温 + 质感，1-2句]
[构图：框架 + 前景/中景/背景，1句]
[约束：排除项 / 不变量，1-2句]
Style: [风格标签]
```

---

## 四、Style 标签速查

| 标签 | 风格 | 最佳适用 |
|------|------|----------|
| `editorial-magazine` | 杂志排版 | 海报、UI |
| `studio-product` | 棚拍产品 | 产品包装 |
| `cinematic-anamorphic` | 变形宽银幕 | 电影质感 |
| `pixar-3d` | 皮克斯 3D | 角色、吉祥物 |
| `kodak-portra-400` | 柯达胶片 | 写实人像 |
| `raw-documentary` | 原始纪实 | 街拍、生活 |

---

## 五、场景模板

### 模板 A：写实摄影（Photorealism）

#### A1：场景人像 / 叙事肖像（Story Portrait）

```
Create a photorealistic candid photograph of a [AGE]-year-old
[ETHNICITY] [GENDER] with [HAIR DESCRIPTION] and [DISTINCTIVE FEATURE].
[动作] while [伴随状态/互动元素].
[LOCATION] — [环境细节1], [环境细节2], [环境细节3].
Shot like a 35mm film photograph, [SHOT TYPE] at [ANGLE],
using a [FOCAL LENGTH] lens.
[LIGHTING: direction, quality, color temperature].
The image should feel [情绪词: honest/unposed/intimate/contemplative],
with real skin texture, worn materials, and everyday detail.
[约束: No glamorization, no heavy retouching, no studio polish.]
```

**情绪词速查**：honest/unposed（纪实）、intimate/warm（私密）、contemplative/powerful（沉思）、raw/gritty（街头）、dreamy/ethereal（梦幻）

#### A2：棚拍人像（Studio Portrait）

```
Photorealistic medium close-up portrait of a [AGE]-year-old
[ETHNICITY] [GENDER] with [HAIR DESCRIPTION] and [DISTINCTIVE FEATURE].
Wearing [CLOTHING], seated in [LOCATION].
Shot on a 35mm full-frame camera with a 50mm f/1.4 lens,
shallow depth of field, golden hour window light from camera left,
3200K warm color temperature.
Natural skin texture with visible pores, sharp focus on eyes,
slight film grain, no smoothing or beauty filter.
Vertical 4:5 framing.
```

#### A3：iPhone 街拍 / 生活快照

> 简洁为王，不要过度结构化。

```
Amateur iPhone photo of [SCENE + 主体 + 动作].
Shot from [ANGLE], natural [TIME OF DAY] light, no flash.
Environment: [2-3 个真实环境细节].
The image should look like a very authentic life slice.
```

#### A4：35mm 胶片风格

```
35mm film photography, [AESTHETIC ADJECTIVE] aesthetic,
soft ambient [LIGHTING TYPE] lighting mixed with gentle natural window light,
subtle film grain, gentle color shift, high atmosphere editorial style,
intimate medium shot, [SUBJECT DESCRIPTION].
[PHYSICAL DETAILS + LIGHTING + POSE & LOCATION]
```

#### A5：RAW 纪实 / 瞬间抓拍

```
Create a completely RAW quality, unprocessed, unedited image
with full iPhone camera quality.
[SCENE — 短句描述场景，保留诗意]
[人物 + 动作 — 简洁，不清单化]
[1-2 个关键环境细节]
```

> 负面约束写法（写实纪实场景）：`负面约束：不要插画、动漫、CGI、棚拍光、过度干净、过度构图、假液体、漂浮物、品牌文字、水印、海报设计感。`

---

### 模板 B：产品 Mockup（Product Photography）

#### B1：标准产品棚拍

```
A close-up product photograph of a [PRODUCT TYPE] standing upright
on a [SURFACE] with a clean [BACKGROUND] backdrop.
The packaging is [MATERIAL] with [TEXTURE], featuring:
- A bold logo "[BRAND]" in [LOGO STYLE]
- A descriptive line "[DESCRIPTION]" below the logo
- A small badge in the upper-right reading "[BADGE TEXT]"
Lighting: large softbox at 45° from camera left,
small fill light from camera right, subtle reflection on the surface.
Shot at f/4, ISO 100, 1/125s, on a 100mm macro lens,
3:4 vertical crop, ultra-sharp focus on the label.
```

**包装类型速查**：咖啡豆→牛皮纸袋+金属箔封口/木桌；护肤品→磨砂玻璃瓶+浮雕瓶盖/大理石；食品罐→哑光铁罐+纸质标签/浅灰水泥；数码配件→高级触感黑盒/深色皮革

#### B2：透明背景产品提取

```
A [PRODUCT] photographed on a transparent/white background.
Clean edges, no color fringing, no light spill.
Studio product photography, soft even lighting,
subtle shadow directly beneath the object.
Sharp focus on the entire product, f/8, 100mm macro lens.
```

#### B3：产品应用场景

```
A [PRODUCT] in use in a [CONTEXT/ENVIRONMENT].
[USER/ACTION DESCRIPTION]
Natural [TIME OF DAY] lighting, lifestyle photography style.
Shot at f/2.8, 35mm lens, eye-level angle.
Focus on the product with the environment softly blurred.
```

---

### 模板 C：电影质感（Cinematic）

```
A cinematic still from an imaginary [GENRE] film,
shot on Kodak Vision3 500T 35mm film stock.
The frame shows [SUBJECT + ACTION] in a [LOCATION]
during [TIME OF DAY].
Color palette: teal shadows and orange highlights,
slight halation around bright areas, organic film grain,
anamorphic 2.39:1 widescreen aspect ratio.
Camera: 40mm lens at f/2, slight motion blur on the foreground,
deep focus on the subject's face.
Mood: [MOOD ADJECTIVES], inspired by the visual language of [DIRECTOR].
```

**风格速查**：Film Noir（高对比黑白/百叶窗阴影）、Coming-of-Age（暖色调/自然光+16mm颗粒）、Cyberpunk（霓虹蓝紫/雨夜湿地反射）、Wabi-sabi（低饱和/柔和窗光）、Denis Villeneuve（橙红渐变+剪影/强背光+反光地板）、Wes Anderson（对称+粉彩色/均匀平面光）

---

### 模板 D：Pixar 3D 角色

> **不套模板**：盲评 0:3 大败。保持简洁。

#### D1：标准模式（推荐）

```
A 3D Pixar-style [SUBJECT], [KEY ACTION/POSE].
[表情+体态描述, 如 large expressive eyes, rosy cheeks, gentle smile].
[1-2 KEY VISUAL DETAILS, e.g. outfit texture, prop, fur/hair detail].
Clean [BACKGROUND TYPE], soft warm lighting, shallow depth of field.
```

4行足矣：第1行角色+动作，第2行表情锚点，第3行视觉细节，第4行背景+光线。

#### D2：极简模式

```
A cute 3D animated [SUBJECT] doing [ACTION].
[Pixar/Disney/Illumination] style, [warm/bright/soft] lighting.
```

---

### 模板 E：App UI Mockup

> 盲评 2:0 大胜——**必须用此模板**。

```
A high-fidelity mobile app screenshot, iPhone 15 Pro frame,
vertical 9:19.5 aspect ratio.
The screen shows a [APP CATEGORY] app with the following layout:
- Top: status bar (9:41, 100% battery, full signal)
- Header: app name "[APP NAME]" in bold, profile icon on the right
- Main: a [HERO COMPONENT] taking 60% of the screen
- Below: [LIST/CARDS/CONTENT BLOCKS]
- Bottom: tab bar with 4 icons (home / explore / notifications / profile)
Design language: [COLOR PALETTE], rounded corners (16px),
subtle drop shadows, system font (SF Pro), [light/dark] mode.
Render the screen pixel-perfect, all text fully legible.
```

---

### 模板 F：信息图（Infographic）

```
Create a detailed infographic about [TOPIC].
Target audience: [AUDIENCE].
Layout: [vertical/vertical scroll/single panel].

Sections (top to bottom):
1. Title: "[TITLE]" — large bold sans-serif, [COLOR]
2. Section 1: [TOPIC] — [ICON] + [STAT/DATA POINT]
3. Section 2: [TOPIC] — [VISUAL ELEMENT] + brief explanation
4. Section 3: [TOPIC] — [CHART/DIAGRAM TYPE]
5. Footer: "[SOURCE/CALL TO ACTION]"

Color palette: [PRIMARY], [SECONDARY], [ACCENT].
Typography: clean sans-serif for body, bold geometric for headers.
Visual style: flat vector illustrations with subtle shadows,
no 3D effects, generous whitespace between sections.
All text must be legible at 100% zoom.
quality="high" recommended for dense text layouts.
```

---

### 模板 G：Logo 设计与品牌系统

> 盲评 2:0 大胜——**必须用此模板**。

#### G1：单 Logo 设计

```
Design a [STYLE: minimalist/geometric/organic/vintage] logo for "[BRAND NAME]",
a [BUSINESS TYPE / INDUSTRY].

Concept: [CORE VISUAL IDEA, e.g. "a leaf shape integrated with the letter E"].
Brand personality: [ADJECTIVE 1], [ADJECTIVE 2], [ADJECTIVE 3].

Visual specs:
- Color: [PRIMARY COLOR] ([HEX CODE]) on pure white background
- Shape: [SYMMETRICAL / ASYMMETRICAL], [GEOMETRIC / ORGANIC] lines
- Weight: [SINGLE STROKE / VARIED THICKNESS], [THIN / MEDIUM / BOLD]
- Layout: centered logo mark with brand name below in [SERIF / SANS-SERIF] font

Constraints: no gradients, no shadows, no 3D effects, no watermarks,
scalable from favicon to billboard, original and non-infringing.
```

**多触点验证**（建议补充）：
```
Also show the logo applied across touchpoints:
- Business card (90×55mm)
- App icon (rounded square)
- Website header
- Signage / billboard
```

#### G2：完整品牌身份包

```
为[业务名]交付一套完整品牌身份系统。

输入信息：
业务描述：[一句话]
行业：[行业]，目标受众：[描述]
品牌个性：[5个关键词]
希望触发的感受：[信任/兴奋/奢华/亲近/力量]

请输出：
1. Logo概念：3-5个完全不同的方向
2. 配色系统：主色+辅助色+强调色+中性色，附HEX
3. 字体系统：标题+正文+强调字体，字号层级
4. 应用触点：名片、App图标、网站首页、社媒模板、广告牌
5. 品牌规则：3条永远不要打破的核心规则
6. 禁用规则清单

设计语言：[现代极简/科技品牌/奢华编辑]，主色[颜色+HEX]，大量留白。
```

#### G3：品牌包络产品广告

```
PHASE 1 / ANCHOR：用 2 行描述[品牌身份]，包括调色板、材质、光影和情绪。
PHASE 2 / INJECT：把[产品]放入这个品牌世界中。
PHASE 3 / FORMAT：指定[输出格式]（hero/方形/竖版story/电商头图）。
PHASE 4 / SIGNATURE：加入[品牌元素]（颗粒/阴影/纹理/包装符号/边框）。
```

---

### 模板 H：等轴微缩场景（Isometric Miniature）

```
A 45° top-down isometric miniature 3D scene of a [SCENE THEME]
diorama on a wooden display base.
Soft refined PBR textures, realistic materials,
clean unified composition, minimalistic aesthetics.
Tiny props integrated into the architecture: [3 SPECIFIC ELEMENTS].
Studio softbox lighting, subtle ambient occlusion,
pastel color palette dominated by [COLOR1] and [COLOR2].
Square 1:1 frame, centered subject, plenty of negative space.
```

---

### 模板 I：创意概念

#### I1：复古交易卡

```
A premium holographic trading card, vertical 3:4 layout.
Center: a [SUBJECT] in dynamic pose, vibrant cinematic lighting.
Border: ornate gold filigree with rune-like icons in four corners.
Top banner reads "[RARITY]" in bold serif caps.
Bottom panel: name plate "[CHARACTER NAME]", three small stat icons
(power / speed / magic) with numeric values.
Holographic foil effect, slight grain, studio backdrop.
```

#### I2：动作人偶吸塑包装

```
A stylized action figure of [SUBJECT] sealed inside a premium
plastic blister pack, photographed straight-on.
The cardboard backing is glossy with a bold header reading
"[BRAND / NAME]" in oversized sans-serif caps and a smaller
tagline "[TAGLINE]".
The figure is posed upright with [ACCESSORY 1] and [ACCESSORY 2]
slotted into molded compartments next to it.
Studio product photography, soft top lighting,
clean off-white background, subtle reflection on the floor.
```

#### I3：360° 全景

```
A 360° equirectangular panoramic photograph of [LOCATION],
aspect ratio 2:1.
The horizon is perfectly level across the middle of the frame.
Foreground (bottom 1/3): [前景].
Mid-ground (middle 1/3): [建筑/人物/场景].
Background (top 1/3): [天空/远景].
Lighting: natural [TIME OF DAY] sun, soft atmospheric haze.
No fish-eye distortion at the poles, ready for VR projection.
```

#### I4：漫画条（Comic Strip）

```
Create a short vertical comic-style reel with [N] equal-sized panels.
Panel 1: [场景 + 动作]
Panel 2: [场景 + 动作]
Panel 3: [场景 + 动作]
Panel 4: [场景 + 动作]
Style: clean line art, flat colors, consistent character design
across all panels.
```

#### I5：概念产品研发拆解板

```
为[产品/家具/装置]生成一张完整的概念产品研发拆解板。

核心概念：把[灵感来源]转译成[产品类型]。
设计哲学：[一句话说明功能与情绪]。

画面结构：
- 中心：高质量 hero render，展示最终产品
- 左侧：观察与形态分析
- 中部：3-5 个演化步骤
- 下方：人体工学或使用场景验证
- 右侧：结构集成与材料方案
- 底部：最终材质、表面纹理、颜色方案和规格表

视觉风格：工业设计提案板，干净白底或浅灰背景。
约束：不要只画一个漂亮产品；必须展示分析、迭代、结构。
```

#### I6：水墨双重曝光人物海报

```
生成一张[人物/角色]的水墨双重曝光人物海报。9:16竖版。
上半区：放大的人物头部或半身剪影。
中下区：全身或半身主体。
剪影内部：融合[关键场景][象征物][叙事片段]。
视觉连接：用云雾、水墨扩散、飞白边缘形成视觉动线。
风格：东方水墨美学 + 写实电影感，克制、高级、留白充足。
```

#### I7：自然科普海报（Apple 风格）

```
生成一张 9:16 竖版高级科普海报，Apple Keynote 风格。

画面结构：
顶部：大标题 [{物种名}]，副标题，英文名，分布信息。
中部：超高清真实立体感 {物种名}，占 50%-70%，白色背景。
底部：四个极简信息栏目，细线 icon + 彩色小标题 + 短说明。
最底部：灰色小字总结。

设计原则：主体极度放大，纯白背景，大量留白，不要圆角卡片/厚边框。
禁止：淡黄旧纸背景、信息图网格、圆角卡片、儿童科普风、卡通风。
```

#### I8：品牌触点系统视觉板

```
为[品牌名]生成一张高端品牌触点系统视觉板。
品牌定位：[行业/生活方式]。
核心气质：[3个关键词]。

触点系统包含：
- 主产品 hero shot
- 包装盒/手提袋/杯子/标签/贴纸等品牌物料
- 菜单卡/价目表/排版样张
- 生活方式场景或用户使用片段
- 配色、字体、图形语言在不同触点的统一应用

设计语言：[现代极简/日式留白/奢华编辑]，大量留白，细腻材质。
```

#### I9：角色动作分解参考表

```
生成一张[角色/人物]动作分解参考表。
风格：[黑白线稿/3D灰阶/漫画分镜/教学图]，背景纯净。
版式：4×4 网格，16 个面板，细线分隔，每格左上角编号 1-16。

角色一致性：所有面板使用同一角色。
每格：动作标题 + 完整身体姿态 + 3-4行动作说明 + 方向箭头/运动轨迹线。
```

#### I10：参考图转 3D 收藏玩具

```
将输入照片转换为高端 3D 收藏玩具形象。
身份保持：保留脸部身份、主要发型、表情气质和服装识别点。
造型比例：大头设计，五官轻微夸张，身体比例玩具化。
材质：哑光 vinyl / resin / collectible figure finish。
灯光：柔和棚拍光，干净背景，主体居中，轮廓清晰。
约束：不要改变身份，不要廉价塑料感，不要文字水印。
```

---

### 模板 J：编辑工作流（Edit）

> 盲评 3:0 大胜——**必须用此模板**。

#### J1：风格迁移
```
Use the same style from the input image and generate [NEW SUBJECT].
Preserve: palette, texture, brushwork, film grain, composition framing.
Change: only the subject/content.
```

#### J2：局部修改
```
Change: replace [SPECIFIC ELEMENT] with [NEW ELEMENT].
Preserve: keep the subject's face, pose, clothing, and lighting
exactly the same as the input.
```

#### J3：光线/天气变换
```
Change: transform the lighting to [NEW LIGHTING CONDITION].
Preserve: identity, geometry, camera angle, object positions.
```

#### J4：多图合成
```
Place the [ELEMENT] from the second image into the setting of image 1,
[POSITION DESCRIPTION]. Use the same style of lighting, composition and background.
```

#### J5：虚拟试穿
```
Edit the image to dress the person using the provided clothing images.
Do not change face, facial features, skin tone, body shape, pose, or identity.
Preserve exact likeness, expression, hairstyle, and proportions.
Match lighting, shadows, and color temperature to the original photo.
```

#### J6：室内设计替换
```
In this room photo, replace ONLY [SPECIFIC ELEMENT] with [NEW ELEMENT].
Preserve camera angle, room lighting, floor shadows, and surrounding objects.
```

#### J7：产品提取（透明背景）
```
Extract the [PRODUCT] from this image and place it on a clean,
transparent background.
Preserve the exact shape, color, texture, and details.
Clean edges, no color fringing, no background remnants.
```

#### J8：草图→渲染
```
Turn this drawing into a photorealistic image.
Preserve the exact layout, proportions, and perspective.
Do not add new elements or text.
```

#### J9：图片翻译（本地化）
```
Translate the text in this image to [TARGET LANGUAGE].
Do not change any other aspect of the image.
Preserve typography style, placement, spacing, and hierarchy.
```

#### J10：服装/产品替换
```
Edit the image to replace the [ORIGINAL PRODUCT] with [NEW PRODUCT].
Do not change the person's face, features, body shape, pose, or identity.
Match lighting, shadows, and color temperature to the original.
```

---

### 模板 K：概念插画 / 场景卡片

> **不套模板**：盲评 0:3 大败。保持叙事性，让模型自己决定构图/配色/光线。

#### K1：场景卡片（带文字）
```
[插画类型] illustration: [核心场景描述，1-2句话].
[Mood/氛围，一个短句].
Style: [视觉风格关键词，2-3个].

Include ONLY this text: "[要出现的文字]"
```

#### K2：故事场景（无文字）
```
A [风格] illustration of [SCENE].
[主体 + 动作].
Mood: [情绪].
```

2-3句话足够。模型会自动补全所有视觉细节。

---

## 六、进阶技巧

### 技巧 1：用约束控制元素数量
```
Constraints: exactly [N] elements, no extra props,
no additional text beyond what's specified above.
```

### 技巧 2：用 Seed 复现构图
```python
img = client.images.generate(
    model="gpt-image-2",
    prompt=PROMPT,
    size="1024x1536",
    quality="high",
    extra_body={"seed": 20260421},
)
```

### 技巧 3：生产级分辨率工作流
| 阶段 | 分辨率 | n | 预算 |
|------|--------|---|------|
| 概念探索 | 1024×1024 | 4 | 10% |
| 构图迭代 | 1024×1536 | 2 | 25% |
| 风格收敛 | 1024×1536 | 1 | 20% |
| 文字精修 | 1024×1536 (edit) | 1 | 15% |
| 最终输出 | 2048×3072 | 1 | 30% |

### 技巧 4：迭代而非过载
从干净基础 prompt 开始，用小的单次修改跟进：
- `"make lighting warmer"`
- `"remove the extra tree"`
- `"shift the subject to the left third"`

---

## 七、常见陷阱

| 陷阱 | 错误做法 | 正确做法 |
|------|----------|----------|
| 1. 塞进一个长句 | 一段话糊成一团 | 分段：场景→主体→细节→光线→约束 |
| 2. 冲突风格 | "photorealistic" + "cartoon" | 只选一个主风格 |
| 3. 负面提示词 | "no watermark, no text" | 改用正面约束 |
| 4. 忽略镜头参数 | 不写焦距和光圈 | 明确指定 |
| 5. 文字不用引号 | 直接写文字 | `"..."` 包裹 |
| 6. 编辑不说清变与不变 | 只说"改背景" | `Change:` / `Preserve:` |

---

## 八、尺寸速查

| 比例 | 像素 | 适用场景 |
|------|------|----------|
| 1:1 | 1024×1024 | Logo、头像、社交媒体 |
| 4:5 | 1024×1280 | Instagram 竖图、人像 |
| 3:4 | 1024×1365 | 交易卡、竖版海报 |
| 16:9 | 1536×864 | 公众号封面、横版主图 |
| 9:16 | 864×1536 | 手机全屏、Stories |
| 2:3 | 1024×1536 | 杂志页、竖版海报 |
| 2:1 | 1536×768 | 360°全景、Banner |
| 2.39:1 | 1536×642 | 电影宽银幕 |

---

## 九、执行流程

### Phase 0：复杂度判断

| 用户输入特征 | 模式 | 处理方式 |
|-------------|------|----------|
| 已是结构化prompt | 简洁模式 | 优化补全，不强行套模板 |
| 一句话需求 | 扩展模式 | 套模板填占位符 |
| 多场景+特定要求 | 定制模式 | 参考模板混合组装 |
| 编辑现有图片 | 编辑模式 | 使用模板 J |
| **创意驱动**（3D卡通/插画） | **跳过模板** | 直接优化，不套模板 |

判断标准：用户输入包含 ≥3 个要素（场景/主体/动作/镜头/光线/风格）→ 简洁模式。

### Phase 1：场景+主题确认

一次性问完（已说清楚的跳过）：

```
1️⃣ 场景类型：🎯写实 | 📦Mockup | 🧸3D卡通 | 🎬电影 | 📱App UI | 🎨Logo | 📊信息图 | 🎃创意 | 🖼️编辑 | 🎭插画 | 🏙️等轴
2️⃣ 核心主体？
3️⃣ 用途？公众号封面/产品展示/品牌VI/社交媒体/PPT
4️⃣ 情绪氛围？温暖/科技/奢华/可爱/神秘/清新
5️⃣ 有参考图吗？
```

### Phase 2：场景深度引导

按场景收集核心参数（见场景分类引导）。

### Phase 3：输出+技术设置

```
📐 尺寸/比例？默认1:1 | 16:9 | 9:16 | 4:5 | 2.39:1
⚙️ 质量？medium(预览) | high(默认)
🔢 几张？默认1张 | 2-4张对比
🔄 A/B双方案？可选一次生成两个方向
```

### Phase 4：输出 prompt + 用户确认

先生成prompt给用户看，不要直接调API。

```
根据你的需求，这是为你定制的 prompt：

---
[完整 prompt 文本]
---

参数：size=1024x1024, quality=high, model=gpt-image-2

1. ✅ 帮我直接生成
2. ✏️ 我想调整
3. 🔄 换个方向
```

### Phase 5：生成后反馈循环

```
- 😍 完美！
- 🔄 微调（用 edit 模式）
- 🔁 重新生成
- 📐 换个尺寸
```

### 质量检查清单

- [ ] 主体在 prompt 开头？
- [ ] 结构分段清晰？
- [ ] 文字用引号包裹？
- [ ] 镜头参数明确？
- [ ] 光线描述具体？
- [ ] 没有堆砌 "8K ultra detailed"？
- [ ] 没有冲突风格？
- [ ] 约束用正面句式？
- [ ] 没有把简单需求过度工程化？
- [ ] 创意类需求是否跳过了模板？

### 默认值策略

- 色调 → warm 暖色调
- 光线 → natural soft light
- 背景 → clean gradient / neutral
- 构图 → centered with padding
- 质量 → high
- 尺寸 → 1:1

---

## 十、混合场景处理

1. **优先识别主场景**：写实 vs 设计 vs 创意
2. **主模板 + 子元素**：以一个模板为主，融入另一个的关键元素
3. **不要硬套多个模板**
4. **完全不确定**：使用通用结构 + 最接近的 Style 标签
5. **简洁优先**：用户输入已很好时不要膨胀

---

## 参考来源

1. OpenAI 官方 Cookbook — GPT Image Generation Models Prompting Guide
2. apiyi.com — GPT-Image-2 prompt collection (April 2026)
3. GitHub ZeroLu/awesome-gpt-image — 社区精选 prompt 集合
4. gptimageai.org — GPT-Image 1.5 Prompt Guide
5. PixVerse — GPT Image 2 Review: Prompt Guide and Use Cases
6. befreed.ai — GPT Image 2: Complete Guide 2026
7. Civitai's Guide to GPT Image 1
8. OpenAI Developer Community — DALL-E 3 & gpt-image-1 tips thread
