# 示例文件说明 | Examples README

本目录包含MERIT Watershed Extractor的使用示例。

## 文件列表

### 1. sample_station_info.xlsx
最小化的Excel示例文件,展示测站信息的标准格式。

**包含字段**:
- 测站编码 (station code)
- 经度 (longitude)
- 纬度 (latitude)
- 集水区面积 (catchment area, km²)

**内容**:
| 测站编码 | 经度    | 纬度   | 集水区面积 |
|----------|---------|--------|------------|
| DEMO_001 | 110.536 | 35.231 | 5000       |
| DEMO_002 | 111.234 | 36.567 | 8500       |
| DEMO_003 | 109.876 | 34.123 | 12000      |

**如何创建**:
由于GitHub不直接支持Excel文件创建,请手动创建此文件:
1. 打开Excel或LibreOffice Calc
2. 复制上表内容
3. 保存为`sample_station_info.xlsx`

### 2. run_single_station.py
演示如何在Python脚本中调用merit_extractor API处理单个站点。

**运行前准备**:
1. 安装merit_extractor: `pip install -e ..`
2. 下载MERIT-Basins数据
3. 修改脚本中的数据路径

**运行**:
```bash
python run_single_station.py
```

**输出**:
- `demo_watershed.gpkg` - 提取的流域边界

### 3. advanced_analysis.ipynb
Jupyter Notebook示例,展示高级流域分析工作流。

**包含内容**:
- 批量流域提取
- 流域形状指标计算
- 空间叠加分析
- 可视化和导出

**运行**:
```bash
jupyter notebook advanced_analysis.ipynb
```

## 快速开始

### 第一步: 安装工具
```bash
cd /path/to/Merit-catchment-extract
pip install -e .
```

### 第二步: 准备数据
1. 下载MERIT-Basins数据 (riv_*.shp 和 cat_*.shp)
2. 准备测站信息Excel文件

### 第三步: 运行示例
```bash
# 方式1: 使用命令行工具
extract-merit -c config.yaml

# 方式2: 运行单站处理示例
cd examples
python run_single_station.py

# 方式3: 运行Jupyter Notebook
jupyter notebook advanced_analysis.ipynb
```

## 更多资源

- 📖 [完整文档](../README.md)
- 📋 [重构计划](../REFACTORING_PLAN.md)
- 🔧 [配置示例](../config.example.yaml)
- 🌐 [MERIT-Basins官网](http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Basins/)

## 故障排除

**问题: ModuleNotFoundError: No module named 'merit_extractor'**
解决: 运行 `pip install -e ..` 安装包

**问题: 找不到数据文件**
解决: 修改示例脚本中的文件路径为实际路径

**问题: 内存不足**
解决: 减小处理的站点数量或使用更大内存的机器
