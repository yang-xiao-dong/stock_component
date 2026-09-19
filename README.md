# 股价监控系统 - 单窗口多股票版本

## 项目简介

这是一个基于Python + pywebview开发的单窗口多股票股价监控系统，支持同时监控10只芯片类股票，提供实时行情、分时图、K线图等功能。

## 功能特点

- 🎯 **单窗口设计**：所有股票在一个窗口中显示，通过快速切换功能操作
- 🔄 **快速切换**：通过上一个/下一个按钮或下拉菜单轻松切换股票
- 📊 **专业图表**：支持分时图和K线图显示，采用Canvas绘制
- 🕐 **实时更新**：5秒刷新一次股价，60秒刷新分时数据
- 🎨 **美观界面**：深色半透明卡片风格，专业美观
- 💼 **股票列表**：瑞芯微、兆易创新、翱捷科技-U、龙迅股份、中科蓝汛、乐鑫科技、晶晨股份、全志科技、恒玄科技、炬芯科技

## 支持的股票

| 代码 | 股票名称 | 类别 | 状态 |
|------|----------|------|------|
| sh603893 | 瑞芯微 | 消费电子 | ✅ 正常 |
| sh603986 | 兆易创新 | 存储芯片 | ✅ 正常 |
| sh688082 | 翱捷科技-U | 通信芯片 | ✅ 正常 |
| sh688222 | 龙迅股份 | 视频芯片 | ✅ 正常 |
| sh688023 | 中科蓝汛 | 网络设备 | ✅ 正常 |
| sh688018 | 乐鑫科技 | AIoT芯片 | ✅ 正常 |
| sh688099 | 晶晨股份 | 多媒体芯片 | ✅ 正常 |
| sh300078 | 全志科技 | 智能芯片 | ⚠️ 部分功能异常 |
| sh688608 | 恒玄科技 | 音频芯片 | ✅ 正常 |
| sh688268 | 炬芯科技 | 智能音频 | ✅ 正常 |

## 安装与运行

### 1. 环境要求

- Python 3.7+
- Windows 10/11
- 网络连接

### 2. 安装依赖

```bash
pip install pywebview requests
```

### 3. 运行程序

```bash
python widget.py
```

或者使用启动脚本（推荐）：
```bash
python run_widget.py
```

启动脚本会自动：
- 检查Python版本
- 检查依赖是否安装
- 自动安装缺少的依赖
- 显示支持的股票列表
- 启动主程序

## 使用说明

1. **启动程序**后，会显示一个悬浮窗口，默认显示瑞芯微(603893)的股票信息
2. **切换股票**：
   - 使用"← 上一个"/"下一个 →"按钮快速切换
   - 点击"▼ 选择股票"下拉菜单查看完整股票列表
   - 显示当前股票位置（如"3 / 10"）
3. **切换图表**：
   - 点击"分时"标签查看分时图
   - 点击"日K"标签查看K线图
4. **窗口操作**：
   - 可以拖动窗口改变位置
   - 支持最小化到托盘
5. **数据更新**：
   - 股价每5秒自动更新
   - 分时图数据每60秒刷新
   - 交易时间外显示"已收盘"状态

## 文件结构

```
G:\stock\
├── widget.py          # 主程序：启动 pywebview 窗口
├── stock_api.py       # 数据获取：腾讯实时行情 + 分时数据 + K线数据
├── ui.html            # 小组件界面（HTML+CSS+JS，含Canvas分时图和K线图）
├── start_widget.bat   # Windows启动脚本
├── test_widget_api.py # API测试脚本
└── README.md          # 项目说明文档
```

## 技术架构

### 后端 (Python)
- **pywebview**: 无界面浏览器窗口容器
- **requests**: HTTP请求库，获取腾讯股票数据
- **多线程**: 后台数据更新，不阻塞UI

### 前端 (HTML/JS/CSS)
- **原生HTML/CSS/JS**: 无外部依赖
- **Canvas**: 专业图表渲染
- **pywebview.api**: Python与JavaScript通信接口

### 数据源
- **实时行情**: `https://qt.gtimg.cn/q={code}`
- **分时数据**: `https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={code}`
- **K线数据**: `https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,60,qfq`

## 接口说明

### Python 接口 (Api类)
```python
def get_realtime(code=None)     # 获取实时行情数据
def get_minute_data(code=None)  # 获取分时数据
def get_kline(code=None)        # 获取K线数据
```

### JavaScript 接口
```javascript
pywebview.api.get_realtime()      // 获取当前股票实时数据
pywebview.api.get_minute_data()  // 获取分时数据
pywebview.api.get_kline()        // 获取K线数据
```

## 故障排除

### 1. 程序无法启动
- 确保Python版本为3.7+
- 检查依赖是否安装：`pip install pywebview requests`

### 2. 数据无法获取
- 检查网络连接
- 确认腾讯接口可用（偶尔可能临时不可用）

### 3. 界面显示异常
- 确保Windows版本为10/11
- 检查系统WebView2是否正常安装

### 4. 性能优化建议
- 关闭不必要的后台程序
- 确保网络带宽充足
- 建议使用SSD硬盘

## 版本历史

### v1.0 (当前版本)
- 单窗口多股票监控系统
- 支持10只芯片类股票
- 实时数据更新
- 专业图表显示
- 股票快速切换功能

## 开发者

基于Python + pywebview技术栈开发
数据源：腾讯股票免费API

## 许可证

MIT License - 自由使用、修改和分发