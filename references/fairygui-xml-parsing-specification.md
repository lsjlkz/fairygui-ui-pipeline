# FairyGUI XML解析规范

## 一、概述

FairyGUI使用XML定义UI组件结构，编辑器将XML编译为二进制格式（`.bytes`文件）供运行时使用。本文档详细说明XML的结构、属性和解析规则。

### 1.1 文件结构

```
UIMake/GameUI/assets/
├── 包名/
│   ├── package.xml          # 包描述文件（资源映射表）
│   ├── 组件1.xml            # 组件定义文件
│   ├── 组件2.xml            # 组件定义文件
│   └── 子目录/              # 可选的组织目录
│       └── 组件3.xml
```

### 1.2 URL组成规则

**URL格式**: `ui://包ID + 资源ID`

- 包ID: 8位字符串，定义在`package.xml`的`id`属性中
- 资源ID: 字符串，定义在`package.xml`的`<component>`的`id`属性中

**示例**: `ui://qoinct2tu7u5e` = 包ID `qoinct2t` + 资源ID `u7u5e`

---

## 二、package.xml 包描述文件

### 2.1 结构示例

```xml
<?xml version="1.0" encoding="utf-8"?>
<packageDescription id="qoinct2t">
  <resources>
    <component id="u7u5e" name="btn_common.xml" path="/button/common/general/" exported="true"/>
    <component id="u7u50" name="progress01.xml" path="/progress_bar/" exported="true"/>
    <image id="sfkmf2" name="bg/common_bg_012_02.png" path="/"/>
    <sound id="zde9e1" name="click.mp3" path="/"/>
  </resources>
  <publish name=""/>
</packageDescription>
```

### 2.2 根节点属性

| 属性 | 类型 | 说明 |
|------|------|------|
| id | string | 包唯一标识（8位随机字符串） |

### 2.3 resources子节点类型

| 节点类型 | 说明 | 关键属性 |
|----------|------|----------|
| component | 组件资源 | id, name, path, exported |
| image | 图片资源 | id, name, path |
| sound | 音效资源 | id, name, path |
| movieclip | 动画资源 | id, name, path |
| font | 字体资源 | id, name, path |
| atlas | 图集资源 | id, name, path |
| misc | 其他资源 | id, name, path |

### 2.4 component节点属性

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 资源唯一标识 |
| name | string | 是 | 资源文件名 |
| path | string | 是 | 资源路径（"/"表示根路径） |
| exported | boolean | 否 | 是否导出（默认false） |

---

## 三、组件XML结构

### 3.1 根节点 `<component>`

```xml
<component size="720,1280" pivot="0.5,0.5" extention="Button" remark="1">
  <!-- 组件内容 -->
</component>
```

#### 3.1.1 根节点属性

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| size | string | 是 | 组件尺寸，格式："宽,高" |
| pivot | string | 否 | 轴心点，格式："x,y"（0-1范围） |
| pivotAsAnchor | boolean | 否 | 是否作为锚点（默认false） |
| extention | string | 否 | 扩展类型（Button/List/Label/ComboBox/ProgressBar/Slider/ScrollBar/Tree） |
| remark | string | 否 | 备注信息 |
| overflow | string | 否 | 溢出类型（visible/hidden/scroll） |
| clipSoftness | string | 否 | 裁剪软度，格式："w,h" |

### 3.2 控制器 `<controller>`

```xml
<controller name="button" exported="true" pages="2,up,3,down" selected="0">
  <action type="play_transition" fromPage="2" toPage="3" transition="down" stopOnExit="true"/>
</controller>
```

#### 3.2.1 controller属性

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 控制器名称 |
| exported | boolean | 否 | 是否导出（默认false） |
| pages | string | 是 | 页面列表，格式："索引1,名称1,索引2,名称2,..." |
| selected | int | 否 | 默认选中页面索引（默认0） |
| homePage | string | 否 | 首页名称或索引 |

#### 3.2.2 action属性

| 属性 | 类型 | 说明 |
|------|------|------|
| type | string | 动作类型（play_transition等） |
| fromPage | string | 源页面索引或名称 |
| toPage | string | 目标页面索引或名称 |
| transition | string | 关联的过渡动画名称 |
| stopOnExit | boolean | 离开页面时是否停止动画 |

### 3.3 显示列表 `<displayList>`

```xml
<displayList>
  <image id="n1_v2ud" name="bg" src="ras1iz" fileName="bg/prog_pub_black.png" pkg="qhqp92rj" xy="0,0" size="680,209"/>
  <text id="n2_k6rq" name="title" xy="20,3" size="206,72" fontSize="48" color="#ffffff"/>
  <component id="n7_m8z5" name="com_account_input" src="m8z51" fileName="account_input.xml" xy="144,369"/>
</displayList>
```

---

## 四、基础组件属性

### 4.1 通用属性（所有组件共享）

| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 组件唯一标识，格式："n数字_包ID后4位" |
| name | string | 是 | 组件名称 |
| xy | string | 是 | 位置，格式："x,y" |
| size | string | 否 | 尺寸，格式："宽,高" |
| pivot | string | 否 | 轴心点，格式："x,y" |
| pivotAsAnchor | boolean | 否 | 是否作为锚点 |
| scale | string | 否 | 缩放，格式："scaleX,scaleY" |
| skew | string | 否 | 倾斜，格式："skewX,skewY" |
| alpha | float | 否 | 透明度（0-1，默认1） |
| rotation | float | 否 | 旋转角度（度，默认0） |
| visible | boolean | 否 | 是否可见（默认true） |
| touchable | boolean | 否 | 是否可触摸（默认true） |
| grayed | boolean | 否 | 是否灰化（默认false） |
| blendMode | string | 否 | 混合模式 |
| customData | string | 否 | 自定义数据 |
| tooltips | string | 否 | 提示文本 |

### 4.1.1 编辑器导出兼容属性

以下属性可能出现在 FairyGUI 编辑器清洗、保存或导出的 XML 中。AI 新生成 XML 时不应随意发明这些属性；但如果 XML 已经过 FairyGUI 编辑器验证、清洗或来自项目现有工程，应允许保留，除非它们导致编辑器报错或引用关系失效。

| 属性 | 常见位置 | 说明 |
|------|----------|------|
| designImageOffsetY | component根节点 | 设计图参考偏移，常用于对齐设计稿 |
| aspect | displayList对象 | 编辑器保存的等比/适配相关标记 |
| group | displayList对象 | 对象所属group的实例ID |
| controller | component实例 | 编辑器保存的控制器初始设置或外部控制参数 |
| advanced | group | 编辑器高级组标记 |
| anchor | displayList对象 | 编辑器锚点/引用标记，区别于规范中的pivotAsAnchor |
| clearOnPublish | loader等对象 | 发布清理相关标记 |
| autoClearText | text等对象 | 文本发布/清理相关标记 |
| autoPlay | transition | 过渡动画自动播放标记 |
| autoPlayRepeat | transition | 过渡动画自动重复次数 |

校验器应区分两种模式：

- **AI新生成模式**：优先使用本规范列出的核心属性；只有Manifest、现有工程XML或用户明确要求时才生成上述兼容属性。
- **编辑器兼容模式**：对已通过 FairyGUI 编辑器打开、保存、清洗或导出的 XML，保留上述兼容属性，不因属性未在核心表中出现而直接判为错误。

### 4.2 滤镜属性

| 属性 | 类型 | 说明 |
|------|------|------|
| filter | string | 滤镜类型（color） |
| filter_brightness | float | 亮度调整（-1到1） |
| filter_contrast | float | 对比度调整（-1到1） |
| filter_saturation | float | 饱和度调整（-1到1） |
| filter_hue | float | 色相调整（-1到1） |

### 4.3 `<image>` 图片组件

```xml
<image id="n1_v2ud" name="bg" src="ras1iz" fileName="bg/prog_pub_black.png" pkg="qhqp92rj" 
       xy="0,0" size="680,209" color="#ffffff" flip="horizontal"/>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| src | string | 源资源ID |
| fileName | string | 文件名 |
| pkg | string | 所属包ID（跨包引用时） |
| color | string | 颜色（#RRGGBB格式） |
| flip | string | 翻转类型（none/horizontal/vertical/both） |
| fillMethod | string | 填充方法（none/horizontal/vertical/radial90/radial180/radial360） |
| fillOrigin | int | 填充起点 |
| fillClockwise | boolean | 是否顺时针填充 |
| fillAmount | float | 填充量（0-1） |
| scale9Grid | string | 九宫格区域，格式："x,y,w,h" |
| tileGridIndice | string | 平铺网格索引 |

### 4.4 `<loader>` 加载器组件

```xml
<loader id="n0_u7u5" name="loader_bg" xy="0,0" size="720,1280" 
        url="ui://ck8jk46vow562" align="center" vAlign="middle" fill="scaleNoBorder"/>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| url | string | 加载资源URL |
| align | string | 水平对齐（left/center/right） |
| vAlign | string | 垂直对齐（top/middle/bottom） |
| fill | string | 填充方式（none/scale/scaleMatchHeight/scaleMatchWidth/scaleFree/scaleNoBorder） |
| shrinkOnly | boolean | 仅缩小 |
| autoSize | boolean | 自动尺寸 |
| showErrorSign | boolean | 显示错误标记 |
| playing | boolean | 是否播放（动画） |
| frame | int | 初始帧（动画） |
| color | string | 颜色 |
| useResize | boolean | 使用缩放（v7+） |

### 4.5 `<text>` 文本组件

```xml
<text id="n7_m8z5" name="richtext_account_input" xy="0,0" size="432,115" 
      fontSize="45" color="#ffffff" align="center" vAlign="middle" leading="6" 
      autoSize="none" singleLine="true" text="test_account" input="true" prompt="请输入账号"/>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| font | string | 字体名称或字体资源URL |
| fontSize | int | 字号 |
| color | string | 颜色（#RRGGBB格式） |
| align | string | 水平对齐（left/center/right） |
| vAlign | string | 垂直对齐（top/middle/bottom） |
| leading | int | 行间距 |
| letterSpacing | int | 字间距 |
| autoSize | string | 自动尺寸（none/both/height/shrink/ellipsis） |
| singleLine | boolean | 单行模式 |
| text | string | 文本内容 |
| ubbEnabled | boolean | UBB解析开关 |
| bold | boolean | 粗体 |
| italic | boolean | 斜体 |
| underline | boolean | 下划线 |
| strikethrough | boolean | 删除线（v3+） |
| strokeColor | string | 描边颜色 |
| strokeSize | float | 描边大小 |
| shadowColor | string | 阴影颜色 |
| shadowOffset | string | 阴影偏移，格式："x,y" |
| input | boolean | 是否为输入框 |
| prompt | string | 输入提示文本 |
| restrict | string | 字符限制 |
| maxLength | int | 最大长度 |
| keyboardType | int | 键盘类型 |
| displayAsPassword | boolean | 密码模式 |

### 4.6 `<richtext>` 富文本组件

继承`<text>`的所有属性，额外支持UBB标签。

### 4.7 `<graph>` 图形组件

```xml
<graph id="n3_xxx" name="rect" xy="0,0" size="100,100" type="rect" lineSize="2" 
       lineColor="#000000" fillColor="#ffffff" roundedRect="true" cornerRadius="10,10,10,10"/>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| type | string | 图形类型（rect/ellipse/polygon/regularPolygon） |
| lineSize | int | 线条宽度 |
| lineColor | string | 线条颜色 |
| fillColor | string | 填充颜色 |
| roundedRect | boolean | 圆角矩形 |
| cornerRadius | string | 圆角半径，格式："左上,右上,右下,左下" |
| polygon | string | 多边形顶点坐标 |
| sides | int | 正多边形边数 |
| startAngle | float | 起始角度 |

### 4.8 `<list>` 列表组件

```xml
<list id="n5_lq68" name="list_planting" xy="0,1" size="680,206" 
      layout="flow_hz" overflow="scroll" colGap="11" lineItemCount="5" 
      defaultItem="ui://q5c3v43slq68r" align="center" vAlign="middle" autoClearItems="true">
  <item/>
  <item/>
</list>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| layout | string | 布局类型（column/row/flow_hz/flow_vz/pagination） |
| overflow | string | 溢出类型（visible/hidden/scroll） |
| scroll | string | 滚动类型（horizontal/vertical/both） |
| lineItemCount | int | 每行/列项目数 |
| lineGap | int | 行间距 |
| colGap | int | 列间距 |
| defaultItem | string | 默认项目URL |
| autoItemSize | boolean | 自动项目尺寸 |
| selectionMode | string | 选择模式（single/multiple/multiple_singleClick/none） |
| align | string | 水平对齐 |
| vAlign | string | 垂直对齐 |
| autoClearItems | boolean | 自动清除项目 |
| childrenRenderOrder | string | 子对象渲染顺序（ascent/descent/arch） |

### 4.9 `<group>` 组组件

```xml
<group id="n8_xxx" name="group1" xy="0,0" layout="horizontal" lineGap="10" columnGap="10" 
       excludeInvisibles="true" autoSizeDisabled="false"/>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| layout | string | 布局类型（none/horizontal/vertical） |
| lineGap | int | 行间距 |
| columnGap | int | 列间距 |
| excludeInvisibles | boolean | 排除不可见子项 |
| autoSizeDisabled | boolean | 禁用自动尺寸 |
| mainGridIndex | int | 主网格索引 |

---

## 五、扩展组件属性

### 5.1 `<Button>` 按钮组件

在`<component>`节点内定义，通过`extention="Button"`标识。

```xml
<component extention="Button">
  <controller name="button" pages="2,up,3,down"/>
  <displayList>
    <loader name="bg" .../>
    <richtext name="title" .../>
  </displayList>
  <Button sound="ui://zde9es2irhi31" title="开始游戏" titleFontSize="40"/>
</component>
```

#### Button属性（在`<Button>`节点内）

| 属性 | 类型 | 说明 |
|------|------|------|
| title | string | 标题文本 |
| titleColor | string | 标题颜色 |
| titleFontSize | int | 标题字号 |
| icon | string | 图标URL |
| selectedTitle | string | 选中时标题 |
| selectedIcon | string | 选中时图标 |
| sound | string | 点击音效URL |
| soundVolumeScale | float | 音效音量比例 |
| mode | string | 按钮模式（common/check/radio） |
| downEffect | string | 按下效果（none/color/darken/scale） |
| downEffectValue | float | 效果值 |
| relatedController | string | 关联控制器名称 |
| relatedPageId | string | 关联页面ID |
| selected | boolean | 选中状态 |

#### 内部子对象约定

- `title`: 标题文本对象
- `icon`: 图标对象
- `button`: 按钮控制器

### 5.2 `<Label>` 标签组件

```xml
<component extention="Label">
  <Label title="标签文本" titleColor="#ffffff" titleFontSize="24"/>
</component>
```

#### Label属性

| 属性 | 类型 | 说明 |
|------|------|------|
| title | string | 标题文本 |
| titleColor | string | 标题颜色 |
| titleFontSize | int | 标题字号 |
| icon | string | 图标URL |

#### 内部子对象约定

- `title`: 标题文本对象
- `icon`: 图标对象

#### 组件实例外部参数写法

当一个组件资源本身是 `extention="Label"`，并且在父组件的 `displayList` 中以 `<component>` 实例方式引用时，FairyGUI 编辑器可能保存如下外部传参写法：

```xml
<component id="n22_v5to" name="com_customer_2" src="rtl3a" fileName="item/customer/com_customer.xml" xy="594,226" size="190,354">
  <Label icon="ui://t8qmfnu2v5to5c"/>
</component>
```

这种 `<Label .../>` 是对被引用 Label 组件的外部属性覆盖/传参，不是伪标签。只要 FairyGUI 编辑器能够打开、清洗并保存该 XML，生成器和校验器应将其视为合法兼容写法。AI 新生成时可以使用该模式，但必须确认目标组件资源确实是 Label 扩展组件，且 `icon/title/titleColor/titleFontSize` 等参数符合 Label 属性表。

### 5.3 `<ComboBox>` 下拉框组件

```xml
<component extention="ComboBox">
  <ComboBox dropdown="ui://xxx/yyy" visibleItemCount="10" popupDirection="down">
    <item text="选项1" value="1" icon="ui://xxx/icon1"/>
    <item text="选项2" value="2" icon="ui://xxx/icon2"/>
  </ComboBox>
</component>
```

#### ComboBox属性

| 属性 | 类型 | 说明 |
|------|------|------|
| title | string | 默认文本 |
| titleColor | string | 标题颜色 |
| icon | string | 默认图标URL |
| dropdown | string | 下拉组件URL |
| visibleItemCount | int | 可见项目数 |
| popupDirection | string | 弹出方向（auto/up/down） |
| selectionController | string | 选择控制器名称 |
| sound | string | 音效URL |
| soundVolumeScale | float | 音效音量比例 |

#### 内部子对象约定

- `title`: 标题文本对象
- `icon`: 图标对象
- `button`: 按钮控制器
- `list`: 下拉列表对象（在dropdown组件内）

### 5.4 `<ProgressBar>` 进度条组件

```xml
<component extention="ProgressBar">
  <ProgressBar titleType="percent" reverse="false" value="50" max="100"/>
</component>
```

#### ProgressBar属性

| 属性 | 类型 | 说明 |
|------|------|------|
| titleType | string | 标题类型（percent/valueAndMax/value/max） |
| reverse | boolean | 反向 |
| value | int | 当前值 |
| min | int | 最小值（v2+） |
| max | int | 最大值 |

#### 内部子对象约定

- `title`: 标题文本对象
- `bar`: 水平进度条对象
- `bar_v`: 垂直进度条对象
- `ani`: 动画对象（可选）

### 5.5 `<Slider>` 滑块组件

```xml
<component extention="Slider">
  <Slider titleType="percent" reverse="false" wholeNumbers="true" changeOnClick="true"/>
</component>
```

#### Slider属性

| 属性 | 类型 | 说明 |
|------|------|------|
| titleType | string | 标题类型 |
| reverse | boolean | 反向 |
| wholeNumbers | boolean | 整数模式（v2+） |
| changeOnClick | boolean | 点击改变值（v2+） |

#### 内部子对象约定

- `title`: 标题文本对象
- `bar`: 水平进度条对象
- `bar_v`: 垂直进度条对象
- `grip`: 滑块手柄对象

### 5.6 `<ScrollBar>` 滚动条组件

```xml
<component extention="ScrollBar">
  <ScrollBar fixedGripSize="true"/>
</component>
```

#### ScrollBar属性

| 属性 | 类型 | 说明 |
|------|------|------|
| fixedGripSize | boolean | 固定滑块大小 |

#### 内部子对象约定

- `grip`: 滑块对象（必需）
- `bar`: 滚动条背景（必需）
- `arrow1`: 箭头按钮1（可选）
- `arrow2`: 箭头按钮2（可选）

### 5.7 `<Tree>` 树组件

继承`<list>`的属性。

---

## 六、Relation关系系统

### 6.1 基本语法

```xml
<loader id="n0_u7u5" name="loader_bg" xy="0,0" size="720,1280">
  <relation target="" sidePair="width-width,height-height"/>
</loader>
```

### 6.2 relation属性

| 属性 | 类型 | 说明 |
|------|------|------|
| target | string | 目标对象ID（空字符串表示parent） |
| sidePair | string | 关系对，多个用逗号分隔 |
| usePercent | boolean | 使用百分比（可选） |

### 6.3 sidePair关系类型

| 关系对 | 说明 |
|--------|------|
| left-left | 左对左 |
| left-center | 左对中 |
| left-right | 左对右 |
| center-center | 中对中 |
| right-left | 右对左 |
| right-center | 右对中 |
| right-right | 右对右 |
| top-top | 上对上 |
| top-middle | 上对中 |
| top-bottom | 上对下 |
| middle-middle | 中对中（垂直） |
| bottom-top | 下对上 |
| bottom-middle | 下对中 |
| bottom-bottom | 下对下 |
| width-width | 宽度关联 |
| width-width% | 宽度百分比关联 |
| height-height | 高度关联 |
| height-height% | 高度百分比关联 |
| size-size | 尺寸关联 |

---

## 七、Gear齿轮系统

### 7.1 基本语法

```xml
<loader id="n1_v2ud" name="bg" ...>
  <gearIcon controller="color" pages="1,0,3,4" 
            values="ui://xxx|ui://yyy|ui://zzz|ui://www" 
            default="ui://xxx"/>
</loader>
```

### 7.2 Gear类型

| Gear类型 | XML标签 | 控制属性 |
|----------|---------|----------|
| GearDisplay | gearDisplay | 可见性 |
| GearXY | gearXY | 位置(x,y) |
| GearSize | gearSize | 尺寸(width,height) + 缩放 |
| GearLook | gearLook | 外观(alpha,rotation,visible,touchable,grayed) |
| GearColor | gearColor | 颜色 |
| GearAnimation | gearAnimation | 动画(playing,frame) |
| GearText | gearText | 文本(text) |
| GearIcon | gearIcon | 图标(icon) |
| GearDisplay2 | gearDisplay2 | 高级可见性（条件显示） |
| GearFontSize | gearFontSize | 字号 |

### 7.3 Gear通用属性

| 属性 | 类型 | 说明 |
|------|------|------|
| controller | string | 关联控制器名称 |
| pages | string | 页面列表，逗号分隔 |
| values | string | 对应值列表，竖线分隔 |
| default | string | 默认值 |

### 7.4 Gear Tween配置

```xml
<gearXY controller="xxx" pages="0,1" values="100,200|300,400">
  <tween easeType="EaseOutQuad" duration="0.3" delay="0.1"/>
</gearXY>
```

| 属性 | 类型 | 说明 |
|------|------|------|
| easeType | string | 缓动类型 |
| duration | float | 持续时间（秒） |
| delay | float | 延迟时间（秒） |
| customEase | string | 自定义缓动曲线（v4+） |

---

## 八、Transition过渡动画

### 8.1 基本语法

```xml
<transition name="up" options="4" frameRate="60">
  <item time="0" type="Scale" tween="true" startValue="0.9,0.9" endValue="1,1" 
        duration="10" ease="Custom" customEase="2,0,0,0.215,1.0025,0.4075,1,1,0,1,1"/>
</transition>
```

### 8.2 transition属性

| 属性 | 类型 | 说明 |
|------|------|------|
| name | string | 动画名称 |
| options | int | 选项标志 |
| frameRate | int | 帧率 |

### 8.3 item属性

| 属性 | 类型 | 说明 |
|------|------|------|
| time | float | 时间点（秒） |
| type | string | 动作类型 |
| tween | boolean | 是否缓动 |
| startValue | string | 起始值 |
| endValue | string | 结束值 |
| duration | float | 持续时间（秒） |
| ease | string | 缓动类型 |
| customEase | string | 自定义缓动曲线 |

### 8.4 TransitionActionType枚举

| 类型 | 说明 |
|------|------|
| XY | 位置变化 |
| Size | 尺寸变化 |
| Scale | 缩放变化 |
| Pivot | 轴心点变化 |
| Alpha | 透明度变化 |
| Rotation | 旋转变化 |
| Color | 颜色变化 |
| Animation | 动画变化 |
| Visible | 可见性变化 |
| Sound | 音效播放 |
| Transition | 嵌套过渡 |
| Shake | 震动效果 |
| ColorFilter | 颜色滤镜 |
| Skew | 倾斜变化 |
| Text | 文本变化 |
| Icon | 图标变化 |

---

## 九、枚举类型定义

### 9.1 PackageItemType（资源类型）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | Image | 图片 |
| 1 | MovieClip | 动画 |
| 2 | Sound | 音效 |
| 3 | Component | 组件 |
| 4 | Atlas | 图集 |
| 5 | Font | 字体 |
| 6 | Swf | Flash（已废弃） |
| 7 | Misc | 其他 |
| 8 | Unknown | 未知 |
| 9 | Spine | Spine动画 |
| 10 | DragoneBones | 龙骨动画 |

### 9.2 ObjectType（对象类型）

| 值 | 类型 | C#类 |
|----|------|------|
| 0 | Image | GImage |
| 1 | MovieClip | GMovieClip |
| 2 | Swf | （废弃） |
| 3 | Graph | GGraph |
| 4 | Loader | GLoader |
| 5 | Group | GGroup |
| 6 | Text | GTextField |
| 7 | RichText | GRichTextField |
| 8 | InputText | GTextInput |
| 9 | Component | GComponent |
| 10 | List | GList |
| 11 | Label | GLabel |
| 12 | Button | GButton |
| 13 | ComboBox | GComboBox |
| 14 | ProgressBar | GProgressBar |
| 15 | Slider | GSlider |
| 16 | ScrollBar | GScrollBar |
| 17 | Tree | GTree |
| 18 | Loader3D | GLoader3D |

### 9.3 AlignType（水平对齐）

| 值 | 类型 |
|----|------|
| 0 | Left |
| 1 | Center |
| 2 | Right |

### 9.4 VertAlignType（垂直对齐）

| 值 | 类型 |
|----|------|
| 0 | Top |
| 1 | Middle |
| 2 | Bottom |

### 9.5 OverflowType（溢出类型）

| 值 | 类型 |
|----|------|
| 0 | Visible |
| 1 | Hidden |
| 2 | Scroll |

### 9.6 FillType（填充类型）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | None | 无 |
| 1 | Scale | 缩放 |
| 2 | ScaleMatchHeight | 高度匹配 |
| 3 | ScaleMatchWidth | 宽度匹配 |
| 4 | ScaleFree | 自由缩放 |
| 5 | ScaleNoBorder | 无边框缩放 |

### 9.7 AutoSizeType（自动尺寸类型）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | None | 无 |
| 1 | Both | 宽高自适应 |
| 2 | Height | 高度自适应 |
| 3 | Shrink | 收缩 |
| 4 | Ellipsis | 省略号 |

### 9.8 ListLayoutType（列表布局类型）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | SingleColumn | 单列 |
| 1 | SingleRow | 单行 |
| 2 | FlowHorizontal | 水平流动 |
| 3 | FlowVertical | 垂直流动 |
| 4 | Pagination | 分页 |

### 9.9 ListSelectionMode（列表选择模式）

| 值 | 类型 |
|----|------|
| 0 | Single |
| 1 | Multiple |
| 2 | Multiple_SingleClick |
| 3 | None |

### 9.10 ProgressTitleType（进度条标题类型）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | Percent | 百分比 |
| 1 | ValueAndMax | 值和最大值 |
| 2 | Value | 当前值 |
| 3 | Max | 最大值 |

### 9.11 ButtonMode（按钮模式）

| 值 | 类型 |
|----|------|
| 0 | Common |
| 1 | Check |
| 2 | Radio |

### 9.12 GroupLayoutType（组布局类型）

| 值 | 类型 |
|----|------|
| 0 | None |
| 1 | Horizontal |
| 2 | Vertical |

### 9.13 FlipType（翻转类型）

| 值 | 类型 |
|----|------|
| 0 | None |
| 1 | Horizontal |
| 2 | Vertical |
| 3 | Both |

### 9.14 FillMethod（填充方法）

| 值 | 类型 | 说明 |
|----|------|------|
| 0 | None | 无 |
| 1 | Horizontal | 水平填充 |
| 2 | Vertical | 垂直填充 |
| 3 | Radial90 | 90度径向填充 |
| 4 | Radial180 | 180度径向填充 |
| 5 | Radial360 | 360度径向填充 |

---

## 十、特殊机制说明

### 10.1 分支(Branch)机制

- Package通过`_branches`数组控制当前分支
- PackageItem通过`getBranch()`获取当前分支对应的资源ID
- 分支前缀会拼接到`pi.name`中（如 `"branch1/itemName"`）

### 10.2 高分辨率(HighResolution)机制

- `getHighResolution()`根据`GRoot.contentScaleLevel`选择对应分辨率的资源ID

### 10.3 字符串表(StringTable)优化

- 二进制格式中所有字符串通过字符串表索引引用
- 避免重复存储相同字符串

### 10.4 版本兼容性

| 版本 | 特性 |
|------|------|
| v2 | 分支/百分比位置 |
| v3 | 删除线/TMP扩展 |
| v4 | 自定义缓动曲线 |
| v5 | 音效支持 |
| v6 | GearAnimation |
| v7 | useResize |

### 10.5 Extension机制

- `PackageItemType.Component`的`extension`字节决定ObjectType
- `UIObjectFactory.ResolvePackageItemExtension`处理自定义类注册
- `ConstructExtension(buffer)`由各组件子类override读取扩展数据

### 10.6 Relations的两次加载

1. **第一次**: 组件自身的Relations（parentToChild=true）
2. **第二次**: 每个子对象的Relations（parentToChild=false）
3. `targetIndex == -1`表示目标是parent

---

## 十一、完整示例

### 11.1 按钮组件示例

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="240,84" pivot="0.5,0.5" extention="Button">
  <!-- 按钮控制器 -->
  <controller name="button" exported="true" pages="2,up,3,down" selected="0">
    <action type="play_transition" fromPage="2" toPage="3" transition="down" stopOnExit="true"/>
    <action type="play_transition" fromPage="3" toPage="2" transition="up" stopOnExit="true"/>
  </controller>
  
  <!-- 颜色控制器 -->
  <controller name="color" exported="true" pages="1,黄,0,绿,2,橙,3,蓝,4,紫" selected="0"/>
  
  <!-- 显示列表 -->
  <displayList>
    <!-- 背景图 -->
    <loader id="n1_v2ud" name="bg" xy="0,0" pivot="0.5,0.5" size="240,84" 
            url="ui://qhqp92rjsfkm7x" align="center" vAlign="middle" fill="scaleFree">
      <!-- 颜色齿轮 -->
      <gearIcon controller="color" pages="1,0,3,4" 
                values="ui://qhqp92rjsfkm7x|ui://qhqp92rjsfkm7z|ui://qhqp92rjsfkm7s|ui://qhqp92rjsfkm6u" 
                default="ui://qhqp92rjsfkm7x"/>
      <!-- 关系 -->
      <relation target="" sidePair="width-width,height-height"/>
    </loader>
    
    <!-- 标题文本 -->
    <richtext id="n2_k6rq" name="title" xy="20,3" pivot="0.5,0.5" size="206,72" 
              touchable="false" font="ui://qdc757xisfkm4" fontSize="48" color="#ffffff" 
              align="center" vAlign="middle" leading="0" letterSpacing="2" autoSize="shrink" 
              bold="true" strokeColor="#000000" strokeSize="0.1" shadowColor="#000000" 
              shadowOffset="0.5,0.1" singleLine="true" text="@你好">
      <relation target="" sidePair="width-width%,height-height%"/>
    </richtext>
  </displayList>
  
  <!-- 按钮属性 -->
  <Button sound="ui://zde9es2irhi31"/>
  
  <!-- 过渡动画 -->
  <transition name="up" options="4" frameRate="60">
    <item time="0" type="Scale" tween="true" startValue="0.9,0.9" endValue="1,1" 
          duration="10" ease="Custom" customEase="2,0,0,0.215,1.0025,0.4075,1,1,0,1,1"/>
  </transition>
  <transition name="down" options="4" frameRate="60">
    <item time="0" type="Scale" tween="true" startValue="1,1" endValue="0.9,0.9" 
          duration="3" ease="Custom" customEase="2,0,0,0.215,1.0025,0.4075,1,1,0,1,1"/>
  </transition>
</component>
```

### 11.2 列表组件示例

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="680,209">
  <displayList>
    <!-- 背景图 -->
    <image id="n1_lq68" name="bg" src="ras1iz" fileName="bg/prog_pub_black.png" 
           pkg="qhqp92rj" xy="0,0" size="680,209">
      <relation target="n5_lq68" sidePair="width-width,height-height,center-center,middle-middle"/>
    </image>
    
    <!-- 列表 -->
    <list id="n5_lq68" name="list_planting" xy="0,1" size="680,206" 
          layout="flow_hz" overflow="scroll" colGap="11" lineItemCount="5" 
          defaultItem="ui://q5c3v43slq68r" align="center" vAlign="middle" autoClearItems="true">
      <item/>
      <item/>
      <item/>
      <item/>
      <item/>
    </list>
  </displayList>
  
  <!-- 组件关系 -->
  <relation target="n5_lq68" sidePair="width-width,height-height"/>
</component>
```

---

## 十二、源代码参考

### 12.1 关键文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| UIPackage.cs | Client/Assets/FairyGUI/Scripts/UI/UIPackage.cs | 包解析 |
| GComponent.cs | Client/Assets/FairyGUI/Scripts/UI/GComponent.cs | 组件解析 |
| GObject.cs | Client/Assets/FairyGUI/Scripts/UI/GObject.cs | 基础对象 |
| FieldTypes.cs | Client/Assets/FairyGUI/Scripts/UI/FieldTypes.cs | 枚举定义 |
| Controller.cs | Client/Assets/FairyGUI/Scripts/UI/Controller.cs | 控制器 |
| Relations.cs | Client/Assets/FairyGUI/Scripts/UI/Relations.cs | 关系系统 |
| GButton.cs | Client/Assets/FairyGUI/Scripts/UI/GButton.cs | 按钮组件 |
| GList.cs | Client/Assets/FairyGUI/Scripts/UI/GList.cs | 列表组件 |
| GGroup.cs | Client/Assets/FairyGUI/Scripts/UI/GGroup.cs | 组组件 |
| Gears/ | Client/Assets/FairyGUI/Scripts/UI/Gears/ | 齿轮系统 |

### 12.2 二进制格式说明

FairyGUI运行时使用二进制格式（`.bytes`文件），魔数`0x46475549`（"FGUI"）。XML在编辑器中编译为二进制，运行时通过`ByteBuffer`解析。

---

## 十三、命名规范

### 13.1 ID生成规则

| ID类型 | 格式 | 长度 | 示例 |
|--------|------|------|------|
| 包ID | 随机字符串（小写字母+数字） | 8位 | `qdf53qpk` |
| 资源ID | 随机字符串（小写字母+数字） | 5位 | `mdvn0` |
| 组件实例ID | `n` + 数字 + `_` + 包ID后4位 | 可变 | `n0_u7u5` |

**ID生成算法**：
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

### 13.2 包命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 包目录名 | 小写字母+下划线 | `login`、`main_panel` |
| 包ID | 8位随机字符串 | `qdf53qpk` |
| package.xml | 固定文件名 | `package.xml` |

### 13.3 组件命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 组件文件名 | 小写字母+下划线+.xml | `login_panel.xml` |
| 组件实例名 | 小写字母+下划线 | `btn_begin`、`list_items` |
| 资源ID | 5位随机字符串 | `mdvn0` |

### 13.4 子对象命名规范

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

### 13.5 控制器命名规范

| 用途 | 命名规则 | 示例 |
|------|----------|------|
| 按钮状态 | `button` | `button` |
| 颜色状态 | `color` | `color` |
| 显示状态 | `state` | `state` |
| 自定义 | 小写字母+下划线 | `tab_index`、`view_mode` |

---

## 十四、资源组织规范

### 14.1 目录结构

```
UIMake/GameUI/assets/
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

### 14.2 图片资源命名

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 背景图 | `bg_{描述}.png` | `bg_main.png` |
| 按钮普通状态 | `btn_{描述}_normal.png` | `btn_confirm_normal.png` |
| 按钮按下状态 | `btn_{描述}_pressed.png` | `btn_confirm_pressed.png` |
| 按钮禁用状态 | `btn_{描述}_disabled.png` | `btn_confirm_disabled.png` |
| 图标 | `icon_{描述}.png` | `icon_gold.png` |
| 头像 | `avatar_{ID}.png` | `avatar_1001.png` |

### 14.3 资源引用规则

**同包引用**：
```xml
<image src="{资源ID}" fileName="{文件名}" />
```

**跨包引用**：
```xml
<image src="{资源ID}" fileName="{文件名}" pkg="{目标包ID}" />
```

---

## 十五、AI自动生成约束

### 15.1 XML生成约束

| 约束类型 | 规则 | 说明 |
|----------|------|------|
| 编码格式 | UTF-8无BOM | 所有XML文件必须使用UTF-8编码 |
| 行尾格式 | CRLF | 使用Windows行尾格式 |
| 缩进 | 2个空格 | 使用2个空格进行缩进 |
| 属性顺序 | 固定顺序 | id、name、xy、size、其他属性 |

### 15.2 属性默认值

| 属性 | 默认值 | 说明 |
|------|--------|------|
| pivot | `0,0` | 默认左上角 |
| alpha | `1` | 默认不透明 |
| rotation | `0` | 默认不旋转 |
| visible | `true` | 默认可见 |
| touchable | `true` | 默认可触摸 |
| grayed | `false` | 默认不灰化 |

### 15.3 组件生成规则

| 组件类型 | 必填属性 | 可选属性 |
|----------|----------|----------|
| component | size | pivot、extention、remark |
| image | id、name、src、fileName | xy、size、color、flip |
| text | id、name、xy、size | fontSize、color、align、vAlign |
| loader | id、name、xy | size、url、align、vAlign、fill |
| list | id、name、xy、size | layout、overflow、colGap、lineItemCount |

### 15.4 关系系统约束

| 约束 | 规则 | 说明 |
|------|------|------|
| 目标引用 | 使用组件ID | relation的target必须引用有效的组件ID |
| 空目标 | 表示父容器 | target=""表示相对于父容器 |
| sidePair格式 | 逗号分隔 | 多个关系对用逗号分隔 |

### 15.5 齿轮系统约束

| 约束 | 规则 | 说明 |
|------|------|------|
| 控制器引用 | 使用控制器名称 | gear的controller必须引用有效的控制器名称 |
| 页面数量 | 与控制器一致 | pages的数量必须与控制器的页面数量一致 |
| 值数量 | 与页面一致 | values的数量必须与pages的数量一致 |

---

## 十六、Manifest到XML映射规范

本章节定义上游资源清单（`asset_manifest.json`、`fgui_manifest.json`）到FairyGUI XML的稳定映射规则。AI生成XML时不得脱离Manifest自行创造资源名、资源ID或组件层级。

### 16.1 Manifest作为唯一真源

| 字段 | 作用 | 下游使用位置 |
|------|------|--------------|
| package.name | 包目录名 | `UIMake/GameUI/assets/{package.name}/` |
| package.id | 包ID | `package.xml`根节点`id` |
| assets[].name | 资源逻辑名 | 资源文件名、组件实例名、代码绑定名 |
| assets[].id | 资源ID | `package.xml`资源节点`id`、`src`引用 |
| assets[].file | 图片或组件文件名 | `fileName`、`name` |
| assets[].type | 资源类型 | `image/component/sound/font/misc`节点类型 |
| assets[].fguiType | UI对象类型 | `image/loader/component/list/text/button` |
| assets[].layer | 所属层级 | `displayList`排序与父子结构 |
| assets[].states | 状态集合 | `controller`、`gearIcon`、`gearDisplay` |
| assets[].pivot | 轴心点 | `pivot`、`pivotAsAnchor` |
| assets[].trim | 是否裁透明边 | 切图脚本和摆放坐标修正 |

### 16.2 推荐Manifest结构

```json
{
  "version": "0.1.0",
  "screen": "CookingView",
  "resolution": [1920, 1080],
  "packages": [
    {
      "name": "cooking",
      "id": "qdf53qpk"
    }
  ],
  "sheets": [
    {
      "name": "sheet_food_5x4",
      "file": "sheet_food_5x4.png",
      "rows": 4,
      "cols": 5,
      "cellSize": [256, 256],
      "padding": 24
    }
  ],
  "assets": [
    {
      "id": "mdvn0",
      "name": "food_patty_raw",
      "file": "food_patty_raw.png",
      "type": "image",
      "fguiType": "loader",
      "package": "cooking",
      "layer": "ingredientLayer",
      "size": [256, 256],
      "pivot": [0.5, 0.5],
      "transparent": true,
      "trim": true,
      "states": ["raw"]
    }
  ]
}
```

### 16.3 映射规则

| Manifest字段 | XML生成规则 |
|--------------|-------------|
| `package.id` | 写入`<packageDescription id="{package.id}">` |
| `assets[type=image]` | 写入`<image id="{id}" name="{file}" path="{path}"/>` |
| `assets[type=component]` | 写入`<component id="{id}" name="{file}" path="{path}" exported="true"/>` |
| `assets[].fguiType=image` | 在组件XML中生成`<image src="{id}" fileName="{file}"/>` |
| `assets[].fguiType=loader` | 在组件XML中生成`<loader url="ui://{package.id}{asset.id}"/>` |
| `assets[].fguiType=button` | 生成`extention="Button"`组件和`<Button>`扩展节点 |
| `assets[].states` | 生成对应`controller`和必要的`gearIcon/gearDisplay` |
| `assets[].layer` | 按层级顺序写入`displayList`，不得跨层插入 |

### 16.4 坐标与裁切修正规则

如果资源经过透明边裁切（`trim=true`），切图脚本必须记录原始格子内的偏移：

```json
{
  "name": "food_patty_raw",
  "sourceCell": [2, 0],
  "originalSize": [256, 256],
  "trimmedSize": [180, 132],
  "trimOffset": [38, 64]
}
```

XML生成器在摆放资源时必须根据`trimOffset`修正`xy`，避免裁切后的资源在FairyGUI中发生视觉偏移。

---

## 十七、ID注册表与稳定生成规则

### 17.1 ID稳定性原则

正式流水线中，ID不得每次重跑都随机生成。首次生成时可以创建ID，后续重跑必须复用已有ID。

| 场景 | 处理规则 |
|------|----------|
| 第一次生成包 | 创建新的包ID并写入`fgui_id_registry.json` |
| 第一次生成资源 | 创建新的资源ID并写入注册表 |
| 修改资源图片 | 保持资源ID不变 |
| 修改组件结构 | 保持组件资源ID不变 |
| 新增资源 | 只为新增资源分配新ID |
| 删除资源 | 标记为`deprecated`，不立即复用ID |
| 重命名资源 | 需要记录`oldName`和`newName`，资源ID默认不变 |

### 17.2 ID注册表示例

```json
{
  "version": "0.1.0",
  "packages": {
    "cooking": {
      "id": "qdf53qpk",
      "createdAt": "2026-06-24"
    }
  },
  "resources": {
    "cooking/food_patty_raw.png": {
      "id": "mdvn0",
      "type": "image",
      "status": "active"
    },
    "cooking/cooking_view.xml": {
      "id": "u7u5e",
      "type": "component",
      "status": "active"
    }
  },
  "deprecated": []
}
```

### 17.3 组件实例ID规则

组件实例ID可以按`displayList`顺序生成，但同一组件文件重跑时应尽量稳定：

```text
n{index}_{packageId后4位}
```

当只新增子对象时，应优先追加新ID，不要重排已有子对象ID。

---

## 十八、自动化边界与人工检查点

### 18.1 自动化等级

| 产物 | 自动化等级 | 说明 |
|------|------------|------|
| `package.xml` | 可自动生成 | 依赖Manifest和ID注册表 |
| 简单组件XML | 可自动生成 | 适合静态图片、文本、基础容器 |
| Button/Label/ProgressBar | 半自动 | 需要人工检查状态和内部子对象命名 |
| List及Item模板 | 半自动 | 需要确认虚拟列表、默认项和渲染逻辑 |
| Relation | 半自动 | 需要适配测试 |
| Gear | 半自动 | 需要校验Controller页面和值数量 |
| Transition | 草稿生成 | 复杂动效应在FairyGUI编辑器内调整 |
| 最终`.bytes`发布包 | 不直接手写 | 必须由FairyGUI编辑器发布 |

### 18.2 人工检查点

| 检查点 | 检查内容 | 不通过时处理 |
|--------|----------|--------------|
| A. UX/UI文档确认 | 界面目标、操作流程、状态是否明确 | 返回需求澄清 |
| B. Manifest确认 | 资源数量、命名、尺寸、状态是否正确 | 修改Manifest后再生图 |
| C. 生图确认 | 风格、透明背景、是否跨格、是否可切 | 局部重生对应资源 |
| D. 切图确认 | 文件名、尺寸、透明边、偏移记录 | 重新切图或修Manifest |
| E. XML校验 | 引用、ID、Controller、Gear、Relation | 修XML或修生成规则 |
| F. FairyGUI导入 | 编辑器能否打开、发布、预览 | 以编辑器报错为准修正 |
| G. Unity接入 | `UIPackage.AddPackage`和绑定代码是否正常 | 修发布资源或绑定代码 |

---

## 十九、XML校验规则

AI生成XML后必须生成`xml_validate_report.json`，至少检查以下规则。

### 19.1 package.xml校验

| 规则 | 错误级别 |
|------|----------|
| 包ID必须存在且为8位小写字母或数字 | error |
| `resources`下所有资源ID不得重复 | error |
| `component/image/sound/font/misc`节点类型必须合法 | error |
| `name`指向的文件必须存在 | error |
| `exported="true"`的组件必须有对应组件XML | error |
| 废弃资源不得被新组件引用 | warning |

### 19.2 组件XML校验

| 规则 | 错误级别 |
|------|----------|
| 根节点必须为`component` | error |
| 根节点必须包含`size` | error |
| `displayList`中的对象ID不得重复 | error |
| `src/url/pkg`引用必须能在package或跨包package中找到 | error |
| `relation target`必须为空或指向有效对象ID | error |
| `gear controller`必须指向有效Controller名称 | error |
| `gear pages`必须是Controller中存在的页面 | error |
| `gear values`数量必须和`pages`数量一致 | error |
| `controller pages`必须为偶数长度的索引/名称序列 | error |
| `transition item type`必须属于合法枚举 | error |
| 文本对象不应写入正式中文文案，除非标记为测试或占位 | warning |
| 已通过FairyGUI编辑器清洗/导出的兼容属性和扩展参数节点不得直接判错 | warning/ignore |

### 19.3 资源校验

| 规则 | 错误级别 |
|------|----------|
| Manifest中的每个资源都必须有实际文件或组件XML | error |
| 图片尺寸应与Manifest记录一致 | warning |
| 需要透明背景的PNG必须含alpha通道 | error |
| Sheet切图数量必须等于`rows * cols`或Manifest声明数量 | error |
| 切图输出文件名必须与Manifest一致 | error |
| `trim=true`的资源必须记录`trimOffset` | warning |

### 19.4 校验报告示例

```json
{
  "ok": false,
  "errors": [
    {
      "file": "cooking_view.xml",
      "code": "MISSING_RESOURCE",
      "message": "loader_food_patty_raw引用的资源ID mdvn0不存在"
    }
  ],
  "warnings": [
    {
      "file": "btn_start.xml",
      "code": "HARDCODED_TEXT",
      "message": "检测到正式文案'开始游戏'，建议改为多语言key"
    }
  ]
}
```

---

## 二十、UI适配与Relation生成策略

### 20.1 默认设计参数

| 项目 | 默认值 |
|------|--------|
| 设计分辨率 | `1920,1080` |
| 屏幕方向 | 横屏 |
| 安全区 | 由Unity侧或顶层UI容器处理 |
| 背景填充 | `scaleNoBorder` |
| 弹窗对齐 | 水平居中、垂直居中 |
| HUD对齐 | 贴边或贴角，使用Relation约束 |

### 20.2 Relation推荐规则

| UI对象 | 推荐Relation |
|--------|--------------|
| 全屏背景 | `width-width,height-height` |
| 居中弹窗 | `center-center,middle-middle` |
| 顶部HUD | `top-top,width-width%` |
| 底部操作区 | `bottom-bottom,width-width%` |
| 左上角货币栏 | `left-left,top-top` |
| 右上角关闭按钮 | `right-right,top-top` |
| 列表容器 | 按父容器宽高或固定尺寸，不默认拉伸Item |

### 20.3 禁止规则

- 不得给所有子对象无脑添加`width-width,height-height`。
- 不得让可拖拽对象跟随父容器缩放，除非Manifest明确要求。
- 不得让背景图承担按钮、列表、文本等交互职责。
- 不得用图片内文字替代`text/richtext`对象。

---

## 二十一、文本与多语言规则

### 21.1 文本生成原则

| 文本类型 | 处理方式 |
|----------|----------|
| 正式UI文案 | 使用文本组件和多语言key |
| 动态数值 | 使用`txt_`前缀文本对象 |
| 测试占位 | 可使用临时文本，但必须标记为`@placeholder` |
| 图片按钮文字 | 禁止烘焙到图片中 |
| 图标数字角标 | 使用文本对象叠加 |

### 21.2 推荐命名

| 类型 | 示例 |
|------|------|
| 标题文本 | `txt_title` |
| 数值文本 | `txt_coin_value` |
| 倒计时文本 | `txt_timer` |
| 按钮标题 | `title` |
| 输入框提示 | `txt_input_prompt` |

### 21.3 多语言Key约定

```xml
<text id="n2_qfpk" name="txt_title" xy="0,0" size="300,60" text="@ui_cooking_title"/>
```

`@`前缀表示该文本需要在运行时或导出阶段接入项目多语言系统。

---

## 二十二、正式流水线产物目录

推荐将UI生产产物和Unity工程资源分离，避免生成过程污染正式工程。

```text
UIProduction/
├── specs/
│   ├── ui_spec.md
│   ├── fgui_spec.md
│   └── fairygui-xml-parsing-specification.md
├── manifests/
│   ├── asset_manifest.json
│   └── fgui_id_registry.json
├── generated/
│   ├── sheets/
│   ├── sliced/
│   └── preview/
├── fgui_xml/
│   └── cooking/
│       ├── package.xml
│       ├── cooking_view.xml
│       └── item_order.xml
└── reports/
    ├── cut_report.json
    ├── xml_validate_report.json
    └── fgui_import_checklist.md
```

进入Unity工程前，应只拷贝经过确认的发布产物和必要源码，不直接依赖生产目录中的临时文件。

---

## 二十三、正式流水线版本

### 23.1 流程定义

```text
用户需求/玩法描述
↓
UX/UI设计文档
↓
资源Manifest与Sheet规划
↓
ImageGen生成背景、单体图、Sheet图
↓
切图脚本生成透明PNG、偏移记录、预览图
↓
FairyGUI XML生成器生成package.xml和组件XML草稿
↓
XML校验器生成xml_validate_report.json
↓
FairyGUI编辑器打开、检查、发布
↓
Unity加载与交互绑定测试
```

### 23.2 版本定位

当前推荐定位为：**半自动UI生产流水线 v0.2**。

| 能力 | 状态 |
|------|------|
| UX/UI文档生成 | 可正式使用 |
| Manifest生成 | 可正式使用 |
| ImageGen出图 | 需要人工挑选和局部返工 |
| Sheet切图 | 可脚本化 |
| XML草稿生成 | 可半自动 |
| XML最终可用性 | 依赖校验器和FairyGUI编辑器确认 |
| Unity接入 | 依赖发布产物和项目加载策略 |

---

## 二十四、常见问题

### 24.1 如何获取组件URL？

```csharp
// 通过包名和资源名
string url = UIPackage.GetItemURL("包名", "资源名");

// 通过PackageItem
PackageItem item = UIPackage.GetItemByURL("ui://包ID资源ID");
```

### 24.2 如何创建组件实例？

```csharp
// 通过URL
GComponent comp = UIPackage.CreateObjectFromURL("ui://包ID资源ID") as GComponent;

// 通过包名和资源名
GComponent comp = UIPackage.CreateObject("包名", "资源名") as GComponent;
```

### 24.3 如何获取子对象？

```csharp
// 通过名称
GObject child = comp.GetChild("name");

// 通过索引
GObject child = comp.GetChildAt(0);

// 获取控制器
Controller ctrl = comp.GetController("controllerName");
```

---

## 二十五、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-05-07 | 初始版本，包含完整的XML解析规范 |
| 1.1 | 2026-05-07 | 补充命名规范、资源组织规范、AI自动生成约束章节 |
| 1.1 | 2026-05-07 | 补充命名规范、资源组织规范、AI自动生成约束章节 |
| 1.2 | 2026-06-24 | 补充Manifest映射、ID注册表、自动化边界、XML校验、UI适配、多语言和正式流水线章节 |
| 1.3 | 2026-06-29 | 补充FairyGUI编辑器导出兼容属性、Label组件实例外部传参写法和对应校验规则 |
