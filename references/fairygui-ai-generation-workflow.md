# FairyGUI AI自动生成流程

> 本文档定义了AI根据业务需求文档和设计图自动生成FairyGUI XML文件和资源的完整流程。

---

## 一、概述

### 1.1 目标

通过AI自动解析业务需求文档和设计图，生成符合FairyGUI规范的XML文件和资源，减少手工编辑工作量，提高UI开发效率。

### 1.2 输入

| 输入类型 | 说明 | 格式要求 |
|----------|------|----------|
| 业务需求文档 | UI功能需求描述 | Markdown/文本格式 |
| 设计图 | UI视觉设计稿 | PNG/JPG/SVG格式 |
| 设计标注 | 尺寸、颜色、字体等标注 | JSON/文本格式（可选） |

### 1.3 输出

| 输出类型 | 说明 | 存放位置 |
|----------|------|----------|
| package.xml | 包描述文件 | `GameUI/assets/{包名}/` |
| 组件XML | UI组件定义文件 | `GameUI/assets/{包名}/` |
| 资源文件 | 图片、音效等资源 | `GameUI/assets/{包名}_image/` |

---

## 二、整体流程

### 2.1 流程图

```
┌─────────────────────────────────────────────────────────────┐
│                        输入阶段                              │
├─────────────────────────────────────────────────────────────┤
│  1. 解析业务需求文档                                          │
│  2. 解析设计图                                               │
│  3. 提取设计标注（尺寸、颜色、字体等）                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        分析阶段                              │
├─────────────────────────────────────────────────────────────┤
│  4. 识别UI组件类型（按钮、列表、输入框等）                      │
│  5. 分析组件层级结构                                         │
│  6. 确定组件属性（尺寸、位置、样式等）                          │
│  7. 识别资源需求（图片、音效、字体等）                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        生成阶段                              │
├─────────────────────────────────────────────────────────────┤
│  8. 生成包ID和资源ID                                         │
│  9. 创建package.xml                                         │
│  10. 创建组件XML文件                                         │
│  11. 处理资源文件（复制、重命名、组织）                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        验证阶段                              │
├─────────────────────────────────────────────────────────────┤
│  12. XML格式验证                                             │
│  13. 属性完整性检查                                          │
│  14. 资源引用验证                                            │
│  15. 生成验证报告                                            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 详细步骤

#### 步骤1：解析业务需求文档

**目标**：理解UI功能需求，识别需要创建的UI组件

**处理内容**：
- 提取UI组件名称和功能描述
- 识别组件类型（面板、弹窗、列表项等）
- 确定组件的交互逻辑

**输出**：组件需求列表

#### 步骤2：解析设计图

**目标**：从设计图中提取UI元素信息

**处理内容**：
- 识别UI元素边界和位置
- 提取文本内容和样式
- 识别图片资源
- 分析组件层级关系

**输出**：UI元素树

#### 步骤3：提取设计标注

**目标**：获取精确的尺寸、颜色、字体等参数

**处理内容**：
- 提取尺寸标注（宽、高）
- 提取颜色值（十六进制）
- 提取字体信息（字体名、字号）
- 提取间距信息（行间距、列间距）

**输出**：设计参数表

#### 步骤4：识别UI组件类型

**目标**：将设计元素映射到FairyGUI组件类型

**映射规则**：

| 设计元素 | FairyGUI组件 | XML标签 |
|----------|--------------|---------|
| 背景图 | 图片组件 | `<image>` 或 `<loader>` |
| 按钮 | 按钮组件 | `<component extention="Button">` |
| 文本标签 | 文本组件 | `<text>` |
| 输入框 | 文本组件（input=true） | `<text input="true">` |
| 列表 | 列表组件 | `<list>` |
| 进度条 | 进度条组件 | `<component extention="ProgressBar">` |
| 下拉框 | 下拉框组件 | `<component extention="ComboBox">` |
| 滑块 | 滑块组件 | `<component extention="Slider">` |
| 图形 | 图形组件 | `<graph>` |
| 容器 | 组件 | `<component>` |

#### 步骤5：分析组件层级结构

**目标**：确定组件的父子关系和嵌套结构

**处理内容**：
- 识别顶层容器
- 确定子组件的包含关系
- 分析组件的布局方式

**输出**：组件层级树

#### 步骤6：确定组件属性

**目标**：为每个组件设置正确的属性

**属性来源**：
- 从设计标注获取尺寸、位置、颜色等
- 从需求文档获取功能属性
- 根据组件类型设置默认属性

#### 步骤7：识别资源需求

**目标**：列出所有需要的资源文件

**资源类型**：
- 图片资源（背景、图标、按钮状态图等）
- 音效资源（点击音效等）
- 字体资源（自定义字体）
- 动画资源（帧动画等）

#### 步骤8：生成包ID和资源ID

**目标**：为包和资源生成唯一标识符

**ID生成规则**：

| ID类型 | 格式 | 长度 | 示例 |
|--------|------|------|------|
| 包ID | 随机字符串 | 8位 | `qdf53qpk` |
| 资源ID | 随机字符串 | 5位 | `mdvn0` |
| 组件实例ID | `n` + 数字 + `_` + 包ID后4位 | 可变 | `n0_u7u5` |

**生成算法**：
```python
import random
import string

def generate_package_id():
    """生成8位包ID"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=8))

def generate_resource_id():
    """生成5位资源ID"""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=5))

def generate_component_instance_id(index, package_id):
    """生成组件实例ID"""
    return f"n{index}_{package_id[-4:]}"
```

#### 步骤9：创建package.xml

**目标**：生成包描述文件

**文件结构**：
```xml
<?xml version="1.0" encoding="utf-8"?>
<packageDescription id="{包ID}">
  <resources>
    <component id="{资源ID}" name="{组件文件名.xml}" path="{路径}" exported="true"/>
    <!-- 更多资源 -->
  </resources>
  <publish name=""/>
</packageDescription>
```

**重要说明**：
- `name`属性必须是完整的xml文件名（如`login_panel.xml`），不是组件名
- `path`属性是组件在包内的相对路径：
  - 根目录：`path="/"`
  - 子目录：`path="/子目录名/"`（如`path="/button/common/"`）
- `id`属性是5位随机字符串，用于生成组件url
- 组件url格式：`ui://包ID资源ID`（如`ui://qdf53qpkmdvn0`）

**生成规则**：
- 每个导出的组件都需要在resources中注册
- 图片资源需要单独注册
- 路径使用相对路径，以`/`开头

#### 步骤10：创建组件XML文件

**目标**：生成组件定义文件

**文件结构**：
```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="{宽},{高}" remark="{备注}">
  <!-- 控制器（可选） -->
  <controller name="{名称}" pages="{页面列表}"/>
  
  <!-- 显示列表 -->
  <displayList>
    <!-- 子组件 -->
  </displayList>
  
  <!-- 扩展属性（可选） -->
  <Button title="{标题}"/>
  
  <!-- 过渡动画（可选） -->
  <transition name="{名称}">
    <item .../>
  </transition>
</component>
```

#### 步骤11：处理资源文件

**目标**：组织和处理资源文件[fairygui-xml-parsing-specification.md](fairygui-xml-parsing-specification.md)

**处理内容**：
- 复制图片资源到对应目录
- 按照命名规范重命名资源
- 生成资源目录结构

**目录结构**：
```
GameUI/assets/
├── {包名}/                    # 组件XML文件
│   ├── package.xml
│   ├── 组件1.xml
│   └── 组件2.xml
└── {包名}_image/              # 图片资源
    ├── bg/
    ├── icon/
    └── btn/
```

#### 步骤12-15：验证阶段

**验证内容**：
- XML格式是否符合规范
- 必填属性是否完整
- 资源引用是否有效
- ID是否唯一

---

## 三、命名规范

### 3.1 包命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 包目录名 | 小写字母+下划线 | `login`、`main_panel` |
| 包ID | 8位随机字符串 | `qdf53qpk` |

### 3.2 组件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 组件文件名 | 小写字母+下划线+.xml | `login_panel.xml` |
| 组件实例名 | 小写字母+下划线 | `btn_begin`、`list_items` |
| 资源ID | 5位随机字符串 | `mdvn0` |

### 3.3 子对象命名

| 组件类型 | 命名前缀 | 示例 |
|----------|----------|------|
| 背景 | `bg_` | `bg_main`、`bg_panel` |
| 按钮 | `btn_` | `btn_confirm`、`btn_cancel` |
| 文本 | `txt_` | `txt_title`、`txt_content` |
| 输入框 | `input_` | `input_name`、`input_password` |
| 列表 | `list_` | `list_items`、`list_friends` |
| 图标 | `icon_` | `icon_gold`、`icon_level` |
| 进度条 | `progress_` | `progress_hp`、`progress_exp` |
| 图片 | `img_` | `img_avatar`、`img_background` |
| 加载器 | `loader_` | `loader_bg`、`loader_icon` |

### 3.4 控制器命名

| 用途 | 命名规则 | 示例 |
|------|----------|------|
| 按钮状态 | `button` | `button` |
| 颜色状态 | `color` | `color` |
| 显示状态 | `state` | `state` |
| 自定义 | 小写字母+下划线 | `tab_index`、`view_mode` |

---

## 四、资源组织规范

### 4.1 目录结构

```
GameUI/assets/
├── {包名}/                    # 组件XML文件
│   ├── package.xml           # 包描述文件
│   ├── 组件1.xml             # 组件定义
│   └── 组件2.xml
└── {包名}_image/             # 图片资源
    ├── bg/                   # 背景图片
    ├── icon/                 # 图标
    ├── btn/                  # 按钮图片
    ├── avatar/               # 头像
    └── effect/               # 特效图片
```

### 4.2 图片资源命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 背景图 | `bg_{描述}.png` | `bg_main.png` |
| 按钮普通状态 | `btn_{描述}_normal.png` | `btn_confirm_normal.png` |
| 按钮按下状态 | `btn_{描述}_pressed.png` | `btn_confirm_pressed.png` |
| 按钮禁用状态 | `btn_{描述}_disabled.png` | `btn_confirm_disabled.png` |
| 图标 | `icon_{描述}.png` | `icon_gold.png` |
| 头像 | `avatar_{ID}.png` | `avatar_1001.png` |

### 4.3 资源引用规则

**重要说明**：`src`属性必须是**资源ID**（5位随机字符串），不是资源名字或文件名。

**同包引用**：
```xml
<image src="{资源ID}" fileName="{文件名}" />
```

**跨包引用**：
```xml
<image src="{资源ID}" fileName="{文件名}" pkg="{目标包ID}" />
```

**示例**：
```xml
<!-- 正确：src是资源ID -->
<image src="ras1iz" fileName="bg/prog_pub_black.png" />

<!-- 错误：src是资源名字 -->
<image src="bg_image" fileName="bg/prog_pub_black.png" />
```

---

## 五、设计图到XML映射规则

### 5.1 布局映射

| 设计布局 | FairyGUI布局 | XML属性 |
|----------|--------------|---------|
| 水平排列 | FlowHorizontal | `layout="flow_hz"` |
| 垂直排列 | FlowVertical | `layout="flow_vz"` |
| 网格排列 | Pagination | `layout="pagination"` |
| 自由定位 | 无 | 使用绝对坐标 `xy="x,y"` |

### 5.2 对齐映射

| 设计对齐 | FairyGUI对齐 | XML属性 |
|----------|--------------|---------|
| 左对齐 | Left | `align="left"` |
| 居中对齐 | Center | `align="center"` |
| 右对齐 | Right | `align="right"` |
| 顶部对齐 | Top | `vAlign="top"` |
| 垂直居中 | Middle | `vAlign="middle"` |
| 底部对齐 | Bottom | `vAlign="bottom"` |

### 5.3 响应式映射

| 设计需求 | FairyGUI关系 | XML配置 |
|----------|--------------|---------|
| 宽度自适应 | width-width | `<relation sidePair="width-width"/>` |
| 高度自适应 | height-height | `<relation sidePair="height-height"/>` |
| 全屏适配 | width-width,height-height | `<relation sidePair="width-width,height-height"/>` |
| 居中显示 | center-center,middle-middle | `<relation sidePair="center-center,middle-middle"/>` |

---

## 六、组件复用规范

### 6.1 复用原则

**当发现以下情况时，应将组件组合提取为独立的组件文件**：

1. **重复出现的UI模式**：同一设计中多次出现相同的UI元素组合
2. **跨面板复用**：多个面板使用相同的组件组合
3. **复杂组件组合**：由多个基础组件组成的可独立功能的单元

### 6.2 常见可复用组件类型

| 组件类型 | 命名格式 | 说明 |
|----------|----------|------|
| 列表项 | `{面板名}_list_item_{序号}.xml` | 列表中的每一项，一个面板可能有多种列表项 |
| 按钮组 | `{面板名}_btn_group_{描述}.xml` | 确认+取消按钮组合 |
| 输入框 | `{面板名}_input_{描述}.xml` | 标签+输入框组合 |
| 进度条 | `{面板名}_progress_{描述}.xml` | 背景+进度条+标题组合 |
| 头像框 | `{面板名}_avatar_{描述}.xml` | 头像+边框+等级组合 |
| 物品格 | `{面板名}_item_{描述}.xml` | 图标+数量+品质框组合 |
| 标签页 | `{面板名}_tab_item_{序号}.xml` | 标签页按钮组合 |

### 6.3 复用组件创建流程

#### 重要说明

1. **组件xml结构**：可复用组件的xml文件结构与面板完全一致，都是以`<component>`为根节点，组件实际上就是较小的面板
2. **url格式**：组件的url格式为`ui://包ID组件ID`，中间没有分隔符（如反斜杠等）

#### 步骤1：识别可复用组合

```
设计图分析
├── 面板A
│   ├── 按钮组合（确认+取消）→ 可复用
│   └── 列表项 → 可复用
├── 面板B
│   ├── 按钮组合（确认+取消）→ 同一复用组件
│   └── 输入框组合 → 可复用
```

#### 步骤2：创建独立组件文件

文件路径：`GameUI/assets/{包名}/{组件名}.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="240,84" remark="1">
  <displayList>
    <component id="n0_xxxx" name="btn_confirm" src="按钮资源ID" fileName="btn_common.xml" xy="0,0">
      <Button title="确认"/>
    </component>
    <component id="n1_xxxx" name="btn_cancel" src="按钮资源ID" fileName="btn_common.xml" xy="120,0">
      <Button title="取消"/>
    </component>
  </displayList>
</component>
```

#### 步骤3：在package.xml中注册

```xml
<component id="{资源ID}" name="btn_group_confirm_cancel.xml" path="/" exported="true"/>
```

#### 步骤4：在面板中引用

```xml
<component id="n5_xxxx" name="btn_group" src="{资源ID}" fileName="btn_group_confirm_cancel.xml" xy="200,500"/>
```

### 6.4 复用判断标准

**应该复用的情况**：
- 同一组合出现3次以上
- 组合包含3个以上子组件
- 组合具有独立的功能语义

**不需要复用的情况**：
- 仅出现1-2次的简单组合
- 组合在不同场景下差异较大
- 复用会导致过度抽象

### 6.5 复用组件命名规范

**重要说明**：所有复用组件的文件名必须动态生成，不能使用固定名称。

#### 命名格式

| 组件类型 | 命名格式 | 示例 |
|----------|----------|------|
| 列表项 | `{面板名}_list_item_{序号}.xml` | `login_panel_list_item_1.xml`、`login_panel_list_item_2.xml` |
| 按钮组 | `{面板名}_btn_group_{描述}.xml` | `shop_panel_btn_group_buy.xml` |
| 输入框 | `{面板名}_input_{描述}.xml` | `register_panel_input_username.xml` |
| 进度条 | `{面板名}_progress_{描述}.xml` | `battle_panel_progress_hp.xml` |
| 头像框 | `{面板名}_avatar_{描述}.xml` | `friend_panel_avatar_player.xml` |
| 物品格 | `{面板名}_item_{描述}.xml` | `reward_panel_item_gold.xml` |
| 标签页 | `{面板名}_tab_item_{序号}.xml` | `setting_panel_tab_item_1.xml` |

#### 命名规则说明

1. **面板名**：使用当前面板的文件名（不含.xml后缀），如`login_panel`、`shop_panel`
2. **序号**：同一面板内同类型组件的序号，从1开始
3. **描述**：组件功能的简短描述，使用小写字母+下划线

#### 示例场景

**场景1**：`login_panel.xml`中有1种列表项
- 列表项文件：`login_panel_list_item_1.xml`
- package.xml注册：`<component id="{资源ID}" name="login_panel_list_item_1.xml" path="/" exported="true"/>`
- 列表引用：`defaultItem="ui://包ID资源ID"`

**场景2**：`shop_panel.xml`中有2种列表项（商品列表、购买记录列表）
- 商品列表项：`shop_panel_list_item_1.xml`
- 购买记录列表项：`shop_panel_list_item_2.xml`
- 商品列表引用：`defaultItem="ui://包ID商品列表项资源ID"`
- 购买记录列表引用：`defaultItem="ui://包ID购买记录列表项资源ID"`

**场景3**：多个面板使用相同的按钮组合
- 每个面板创建自己的按钮组合文件：`panel_a_btn_group_confirm.xml`、`panel_b_btn_group_confirm.xml`
- 或者如果完全相同，可以创建一个通用的：`common_btn_group_confirm.xml`

---

## 七、常见UI模式模板

### 7.1 弹窗面板模板

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="600,400" remark="1">
  <displayList>
    <!-- 背景 -->
    <loader id="n0_xxxx" name="bg" xy="0,0" size="600,400" url="ui://包ID背景资源ID">
      <relation target="" sidePair="width-width,height-height"/>
    </loader>
    
    <!-- 标题 -->
    <text id="n1_xxxx" name="txt_title" xy="0,20" size="600,50" fontSize="36" color="#ffffff" 
          align="center" vAlign="middle" text="弹窗标题">
      <relation target="" sidePair="center-center"/>
    </text>
    
    <!-- 内容区域 -->
    <component id="n2_xxxx" name="content" xy="50,80" size="500,250">
      <!-- 内容组件 -->
    </component>
    
    <!-- 关闭按钮 -->
    <component id="n3_xxxx" name="btn_close" src="按钮资源ID" fileName="btn_close.xml" xy="560,10">
      <Button/>
    </component>
    
    <!-- 确认按钮 -->
    <component id="n4_xxxx" name="btn_confirm" src="按钮资源ID" fileName="btn_common.xml" xy="200,340">
      <Button title="确认"/>
    </component>
    
    <!-- 取消按钮 -->
    <component id="n5_xxxx" name="btn_cancel" src="按钮资源ID" fileName="btn_common.xml" xy="350,340">
      <Button title="取消"/>
    </component>
  </displayList>
</component>
```

**说明**：
- `xxxx`为包ID后4位，实际生成时需替换为真实值
- `src`属性必须是**资源ID**（5位随机字符串），不是资源名字
- `fileName`属性是资源文件名

### 6.2 列表项模板

**重要说明**：列表项必须单独创建为一个组件xml文件，然后在列表中通过`defaultItem`属性引用其url。列表项文件名必须动态生成。

#### 列表项组件文件（单独创建）

文件路径：`GameUI/assets/{包名}/{面板名}_list_item_{序号}.xml`

**示例**：`login_panel_list_item_1.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="680,100" remark="1">
  <displayList>
    <!-- 背景 -->
    <image id="n0_xxxx" name="bg" src="背景资源ID" fileName="bg_list_item.png" xy="0,0" size="680,100">
      <scale9Grid x="10" y="10" w="660" h="80"/>
    </image>
    
    <!-- 图标 -->
    <loader id="n1_xxxx" name="icon" xy="10,10" size="80,80" url="ui://包ID图标资源ID"/>
    
    <!-- 标题 -->
    <text id="n2_xxxx" name="txt_title" xy="100,10" size="200,40" fontSize="28" color="#ffffff" 
          text="列表项标题"/>
    
    <!-- 描述 -->
    <text id="n3_xxxx" name="txt_desc" xy="100,50" size="400,40" fontSize="20" color="#cccccc" 
          text="列表项描述"/>
    
    <!-- 操作按钮 -->
    <component id="n4_xxxx" name="btn_action" src="按钮资源ID" fileName="btn_small.xml" xy="580,30">
      <Button title="操作"/>
    </component>
  </displayList>
</component>
```

#### package.xml中注册列表项

```xml
<component id="{列表项资源ID}" name="{面板名}_list_item_{序号}.xml" path="/" exported="true"/>
```

#### 在面板中引用列表项

```xml
<list id="n5_xxxx" name="list_items" xy="0,100" size="680,500" 
      layout="flow_hz" overflow="scroll" colGap="11" lineItemCount="5" 
      defaultItem="ui://包ID列表项资源ID" align="center" vAlign="middle">
  <item/>
  <item/>
  <item/>
</list>
```

**说明**：
- `xxxx`为包ID后4位，实际生成时需替换为真实值
- `src`属性必须是**资源ID**（5位随机字符串），不是资源名字
- `fileName`属性是资源文件名
- `defaultItem`必须是**url格式**：`ui://包ID资源ID`，其中资源ID必须是package.xml中注册的列表项资源ID
- 列表项必须在package.xml中注册为独立的组件资源

**示例**：
```xml
<!-- package.xml -->
<packageDescription id="qdf53qpk">
  <resources>
    <component id="abc12" name="login_panel_list_item_1.xml" path="/" exported="true"/>
  </resources>
</packageDescription>

<!-- 面板中引用 -->
<list defaultItem="ui://qdf53qpkabc12" ...>
```

### 6.3 输入框模板

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="400,60" remark="1">
  <displayList>
    <!-- 背景 -->
    <image id="n0_xxxx" name="bg" src="背景资源ID" fileName="bg_input.png" xy="0,0" size="400,60">
      <scale9Grid x="10" y="10" w="380" h="40"/>
    </image>
    
    <!-- 输入文本 -->
    <text id="n1_xxxx" name="input_text" xy="10,10" size="380,40" fontSize="24" color="#ffffff" 
          input="true" prompt="请输入内容" maxLength="100"/>
  </displayList>
</component>
```

**说明**：
- `xxxx`为包ID后4位，实际生成时需替换为真实值
- `src`属性必须是**资源ID**（5位随机字符串），不是资源名字
- `fileName`属性是资源文件名

### 6.4 进度条模板

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="300,30" extention="ProgressBar" remark="1">
  <displayList>
    <!-- 背景 -->
    <image id="n0_xxxx" name="bg" src="背景资源ID" fileName="bg_progress.png" xy="0,0" size="300,30">
      <scale9Grid x="5" y="5" w="290" h="20"/>
    </image>
    
    <!-- 进度条 -->
    <image id="n1_xxxx" name="bar" src="进度条资源ID" fileName="progress_bar.png" xy="0,0" size="300,30">
      <scale9Grid x="5" y="5" w="290" h="20"/>
    </image>
    
    <!-- 标题 -->
    <text id="n2_xxxx" name="title" xy="0,0" size="300,30" fontSize="18" color="#ffffff" 
          align="center" vAlign="middle"/>
  </displayList>
  
  <ProgressBar titleType="percent" value="50" max="100"/>
</component>
```

**说明**：
- `xxxx`为包ID后4位，实际生成时需替换为真实值
- `src`属性必须是**资源ID**（5位随机字符串），不是资源名字
- `fileName`属性是资源文件名

---

## 七、验证规则

### 7.1 属性白名单

**重要说明**：每个组件类型只能使用规范中定义的属性，不得添加未定义的属性。

#### 通用属性（所有组件可用）
```
id, name, xy, size, pivot, pivotAsAnchor, scale, skew, alpha, rotation, 
visible, touchable, grayed, blendMode, customData, tooltips
```

#### image组件属性
```
src, fileName, pkg, color, flip, fillMethod, fillOrigin, fillClockwise, 
fillAmount, scale9Grid, tileGridIndice
```

#### text组件属性
```
font, fontSize, color, align, vAlign, leading, letterSpacing, autoSize, 
singleLine, text, ubbEnabled, bold, italic, underline, strikethrough, 
strokeColor, strokeSize, shadowColor, shadowOffset, input, prompt, 
restrict, maxLength, keyboardType, displayAsPassword
```

#### loader组件属性
```
url, align, vAlign, fill, shrinkOnly, autoSize, showErrorSign, playing, 
frame, color, useResize
```

#### list组件属性
```
layout, overflow, scroll, lineItemCount, lineGap, colGap, defaultItem, 
autoItemSize, selectionMode, align, vAlign, autoClearItems, childrenRenderOrder
```

#### component组件属性
```
size, pivot, pivotAsAnchor, extention, remark, overflow, clipSoftness
```

### 7.2 XML格式验证

| 检查项 | 规则 | 错误提示 |
|--------|------|----------|
| XML声明 | 必须包含 `<?xml version="1.0" encoding="utf-8"?>` | 缺少XML声明 |
| 根节点 | 必须是 `<component>` 或 `<packageDescription>` | 根节点错误 |
| 标签闭合 | 所有标签必须正确闭合 | 标签未闭合 |
| 属性引号 | 所有属性值必须用引号包围 | 属性值缺少引号 |

### 7.2 属性完整性检查

| 组件类型 | 必填属性 | 检查规则 |
|----------|----------|----------|
| component | size | 必须包含尺寸 |
| image | id, name, src, fileName | 必须包含资源引用 |
| text | id, name, xy, size | 必须包含位置和尺寸 |
| loader | id, name, xy | 必须包含位置 |
| list | id, name, xy, size | 必须包含位置和尺寸 |

**重要说明**：`displayList`中的所有子组件**必须**包含`id`属性，格式为`n{数字}_{包ID后4位}`（如`n0_u7u5`）。缺少id属性会导致FairyGUI无法正确识别组件。

### 7.3 资源引用验证

| 检查项 | 规则 | 错误提示 |
|--------|------|----------|
| 包ID存在 | package.xml中的id必须存在 | 包ID不存在 |
| 资源ID存在 | 引用的资源ID必须在package.xml中注册 | 资源ID不存在 |
| 文件存在 | 引用的文件必须实际存在 | 文件不存在 |
| 跨包引用 | 跨包引用的包必须存在 | 引用的包不存在 |

### 7.4 ID唯一性检查

| 检查项 | 规则 | 错误提示 |
|--------|------|----------|
| 包ID唯一 | 不同包的ID不能相同 | 包ID重复 |
| 资源ID唯一 | 同一包内资源ID不能重复 | 资源ID重复 |
| 组件实例ID唯一 | 同一组件内实例ID不能重复 | 实例ID重复 |

---

## 八、错误处理

### 8.1 常见错误类型

| 错误类型 | 说明 | 处理方式 |
|----------|------|----------|
| 设计图解析失败 | 无法识别设计图内容 | 提示用户提供更清晰的设计图 |
| 属性值无效 | 属性值不符合规范 | 使用默认值并记录警告 |
| 资源缺失 | 引用的资源不存在 | 生成占位资源并记录警告 |
| ID冲突 | ID重复 | 重新生成ID |

### 8.2 警告处理

| 警告类型 | 说明 | 处理方式 |
|----------|------|----------|
| 默认值使用 | 使用了默认属性值 | 记录日志，提示用户确认 |
| 资源降级 | 使用了替代资源 | 记录日志，提示用户替换 |
| 布局调整 | 自动调整了布局 | 记录日志，提示用户检查 |

---

## 九、工具集成

### 9.1 命令行接口

```bash
# 生成单个组件
python fairygui_generator.py --input design.png --output login/login_panel.xml

# 生成整个包
python fairygui_generator.py --input design_folder/ --output login/ --package login

# 验证XML文件
python fairygui_validator.py --input login/login_panel.xml
```

### 9.2 配置文件

```json
{
  "project_root": "GameUI/assets",
  "default_size": "720,1280",
  "default_font_size": 24,
  "default_color": "#ffffff",
  "id_generation": "random",
  "resource_organization": "by_type"
}
```

---

## 十、最佳实践

### 10.1 设计图准备

1. **使用标准分辨率**：建议使用720x1280或1080x1920
2. **分层设计**：背景、内容、交互元素分层
3. **标注清晰**：提供完整的尺寸、颜色、字体标注
4. **命名规范**：设计图中的图层使用规范命名

### 10.2 需求文档编写

1. **组件功能描述**：清晰描述每个组件的功能
2. **交互逻辑**：说明组件的交互行为
3. **状态说明**：说明组件的不同状态（正常、按下、禁用等）
4. **数据绑定**：说明需要动态显示的数据

### 10.3 生成后检查

1. **视觉对比**：将生成的UI与设计图对比
2. **功能测试**：测试交互功能是否正常
3. **性能检查**：检查资源大小和加载性能
4. **兼容性测试**：测试不同分辨率下的显示效果

---

## 十一、AI生成要求

### 11.1 基本要求

1. 生成符合FairyGUI规范的XML结构
2. 包含component根节点，设置合适的size属性
3. 根据图片内容识别UI组件（如按钮、标签、列表等）
4. 为每个组件设置合适的xy坐标和size尺寸
5. 使用规范的组件命名（遵循第三章命名规范）
6. 如果有需要，添加controller和group
7. 组件id使用规范格式：n + 数字 + _ + 随机4位字符（如n0_u7u5）
8. 直接输出XML内容，不要包含其他解释文字
9. 包含XML声明：`<?xml version="1.0" encoding="utf-8"?>`
10. remark属性必须使用数字（通常为"1"），不要使用中文描述

### 11.2 输出格式要求

- 输出必须是纯XML内容，不要包含markdown代码块标记
- 不要包含任何解释性文字或注释
- XML标签必须正确闭合
- 属性值必须用双引号包围

---

## 十二、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-07 | 初始版本，包含完整的AI自动生成流程 |
| 1.1 | 2026-05-07 | 新增"AI生成要求"章节，整合脚本中的通用描述模板 |
| 1.2 | 2026-05-07 | 新增"组件复用规范"章节，明确可复用组件应单独创建xml文件 |
| 1.3 | 2026-05-07 | 完善组件复用命名规范，所有复用组件文件名必须动态生成 |
| 1.4 | 2026-05-07 | 明确组件xml结构与面板一致，修正url格式为`ui://包ID组件ID` |
| 1.5 | 2026-05-07 | 修正remark属性用法，统一使用数字（通常为"1"）而非中文描述 |
| 1.6 | 2026-05-07 | 完善package.xml说明，明确name必须是xml文件名，path是文件夹路径；明确defaultItem url必须与package.xml中的id关联 |
