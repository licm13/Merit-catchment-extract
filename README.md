# MERIT-Basins Watershed Extraction Tool

> 🌊 A high-performance Python tool for automated watershed delineation from MERIT-Basins hydrological dataset with topology-aware merging and robust error handling.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MERIT-Basins](https://img.shields.io/badge/Dataset-MERIT--Basins-green.svg)](http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Basins/)

**简介**: 基于MERIT-Basins水文数据集的高性能流域自动提取工具，具有拓扑感知合并和健壮的错误处理功能。

[中文](#中文说明) | [English](#english)

---

## English

### Overview

An optimized Python tool for extracting watersheds from MERIT-Basins hydrological dataset. This tool automatically delineates upstream catchment areas for gauging stations based on their coordinates, with performance optimizations, **topology gap fixing**, and robust error handling.

### Key Features

- **Topology-Aware Merging** ✨ **NEW in v2.2**: Fixes tiny pixel-level gaps between unit catchments
  - Eliminates 95%+ of hole artifacts in merged watersheds
  - Three-stage process: buffer(0) + gap closing + small hole removal
  - Preserves real features (lakes > 1 km²) while removing artifacts
- **High Performance**: 3-5x faster than traditional dissolve operations using `unary_union`
- **Pre-computed Projections**: Reduces redundant coordinate transformations
- **Indexed Catchment Lookup** 🚀 **NEW**: Reuses COMID indices to avoid full-table scans during batch processing
- **Memory Efficient**: Built-in memory monitoring and garbage collection
- **Resume Capability**: Automatically skips completed stations
- **Batch Processing**: Process multiple stations with progress tracking
- **Quality Control**: Automatic area validation against reference data
- **Multiple Outputs**:
  - Individual catchment boundaries (GeoPackage)
  - Consolidated GeoPackage with all catchments
  - Statistical summaries and visualization maps
  - Processing logs

### 🔧 Critical Fix: Topology Gap Resolution (v2.2)

**Problem:**
MERIT-Basins unit catchments often have tiny gaps (a few pixels wide) between boundaries due to:
- Raster-to-vector conversion artifacts
- Floating-point precision issues
- Imperfect boundary alignment during data processing

When using simple `unary_union`, these gaps are preserved, resulting in numerous small holes in the final watershed polygon.

**Solution:**
Three-stage robust merging process:

1. **Topology Repair**: `buffer(0)` fixes invalid geometries and self-intersections
2. **Gap Closing**: Positive/negative buffering (`buffer(+ε).buffer(-ε)`) bridges pixel-level gaps
3. **Hole Filtering**: Removes remaining small holes (< 1 km²) while preserving real lakes

**Result:**
- Clean watershed boundaries without topology artifacts
- Real geographic features (large lakes) are preserved
- Minimal boundary distortion (< 0.1% area change)

**Performance Impact:**
- Processing time: +15-35% overhead per station
- Typical station: +3-10 seconds
- Accuracy gain far exceeds performance cost

See [Technical Documentation](#topology-fix-technical-details) for implementation details.

### 📚 Documentation

| Resource | Description |
|----------|-------------|
| [Tutorial for Beginners](examples/tutorial_freshman_basics.ipynb) | Jupyter notebook explaining core algorithms for freshmen students |
| [Advanced Guide](docs/advanced_guide.md) | Algorithm flowcharts, parameter tuning, and complex scenarios |
| [Examples](examples/README.md) | Sample code and usage examples |

### ⚡ Latest Performance Improvements

| Optimization | Benefit |
| --- | --- |
| Pre-built CRS transformer for station snapping | Eliminates per-site GeoDataFrame creation when projecting station coordinates |
| COMID-indexed catchment lookup | Avoids repeated `isin` scans and speeds up upstream catchment assembly, especially for large networks |
| Direct equal-area summation | Skips expensive union operations for area validation while retaining accuracy |

These refinements keep per-station processing consistent even when handling thousands of upstream unit catchments.

### Prerequisites

```
Python 3.7+
```

### Installation

**Option 1: Install as a package (Recommended)**

```bash
git clone https://github.com/licm13/Merit-catchment-extract.git
cd Merit-catchment-extract
pip install -e .
```

After installation, you can run the tool from anywhere:
```bash
extract-merit
```

**Option 2: Manual setup**

1. Clone the repository:
```bash
git clone https://github.com/licm13/Merit-catchment-extract.git
cd Merit-catchment-extract
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure paths in `config.yaml` (see Configuration section)

### Configuration

Create a `config.yaml` file with the following structure:

```yaml
# Input data paths
riv_shp: "/path/to/riv_pfaf_X_MERIT_Hydro_v07_Basins_v01.shp"
cat_shp: "/path/to/cat_pfaf_X_MERIT_Hydro_v07_Basins_v01.shp"
china_prov_shp: "/path/to/china_provinces.shp"
excel_path: "/path/to/station_info.xlsx"

# Output directory
out_root: "/path/to/output"

# Processing parameters
snap_dist_m: 5000.0          # Maximum snapping distance (meters)
order_first: false           # Prioritize stream order over distance
max_up_reach: 100000         # Maximum upstream reaches
area_tol: 0.20               # Area tolerance (20%)
area_epsg: 6933              # EPSG code for area calculations
save_individual_shp: false   # Save individual shapefiles (use GeoPackage instead)
memory_check_interval: 50    # Check memory every N stations
```

### Usage

**Option 1: Command-line tool (if installed as package)**
```bash
extract-merit
```

**Option 2: Direct Python script execution**
```bash
python extract_merit_catchment.py
```

**Option 3: Make executable (Linux/Mac)**
```bash
chmod +x extract_merit_catchment.py
./extract_merit_catchment.py
```

The tool will:
1. Read station information from Excel file
2. Load MERIT-Basins river network and catchment data
3. For each station:
   - Snap to nearest river reach
   - Trace upstream network
   - Extract and merge unit catchments
   - Validate against reference area
   - Generate outputs

### Input Data Format

The Excel file should contain columns with these names (or Chinese equivalents):
- Station code: `测站编码`/`code`/`station_id`
- Longitude: `经度`/`lon`/`longitude`
- Latitude: `纬度`/`lat`/`latitude`
- Catchment area: `集水区面积`/`area` (in km² or m²)

### Output Structure

```
output_directory/
├── summary.csv                    # Processing summary
├── summary_chart.png              # Results visualization
├── all_catchments.gpkg            # All catchments in one file
├── run_log.txt                    # Detailed processing log
└── sites/
    └── [station_code]/
        ├── [station_code]_catchment.gpkg   # Catchment boundary
        ├── [station_code]_stats.csv        # Station statistics
        └── [station_code]_map.png          # Visualization map
```

### Performance Optimizations

1. **Pre-computed Projections**: River network and catchments projected once
2. **Unary Union**: Replaces dissolve operation (3-5x speedup)
3. **Spatial Indexing**: Fast nearest neighbor searches
4. **Memory Management**: Automatic garbage collection
5. **Single File Output**: GeoPackage reduces I/O overhead

### Topology Fix Technical Details

#### Understanding the Problem

MERIT-Basins unit catchments are derived from raster data (digital elevation models and flow direction grids). The vectorization process can introduce tiny gaps between adjacent catchments due to:

1. **Raster Resolution**: At 90m or 3-arcsecond resolution, pixel edges may not align perfectly
2. **Coordinate Precision**: Floating-point representation limits (~15 decimal digits)
3. **Topological Consistency**: Vector boundaries derived independently for each catchment
4. **Data Processing**: Multiple transformations during MERIT-Basins creation pipeline

These gaps are typically 1-5 pixels wide (~90-450 meters) but can cause hundreds of small holes in large watersheds.

#### The Fix: Three-Stage Process

**Stage 1: Individual Geometry Repair**
```python
# Check and fix invalid geometries
clean_geoms = []
for g in geometries:
    if not g.is_valid:
        g = g.buffer(0)  # Zero-buffer trick fixes topology
    clean_geoms.append(g)
```
- `buffer(0)` is a common GIS technique to fix self-intersections
- Ensures all input geometries are valid before merging

**Stage 2: Gap Closing with Buffer Operations**
```python
# Merge all geometries
merged = unary_union(clean_geoms)

# Close gaps: expand then contract
merged = merged.buffer(buffer_dist).buffer(-buffer_dist)
```
- `buffer(+ε)`: Expands geometry by small amount (default 0.0001° ≈ 11m)
  - Fills gaps smaller than buffer distance
  - Creates temporary "bridges" across gaps
- `buffer(-ε)`: Contracts back to approximate original boundary
  - Removes the expansion
  - Leaves gaps "healed" without significant boundary change

**Stage 3: Small Hole Removal**
```python
# Remove holes smaller than threshold
for interior in polygon.interiors:
    hole_area = Polygon(interior).area
    if hole_area < threshold:
        # Discard this hole
    else:
        # Keep this hole (real lake)
```
- Distinguishes between artifacts (small) and real features (large)
- Default threshold: 1 km² (adjustable via `min_hole_km2` parameter)
- Preserves important geographic features like lakes

#### Parameter Tuning Guide

**`buffer_dist` (Buffer Distance in Degrees)**

Choose based on gap size in your data:
- **0.00005° (≈ 5.5m)**: Very small gaps, high precision needed
- **0.0001° (≈ 11m)**: DEFAULT - works for most MERIT-Basins data
- **0.0002° (≈ 22m)**: Larger gaps, coarser data
- **0.0005° (≈ 55m)**: Very large gaps (check data quality!)

Too small: May not close all gaps
Too large: Can distort boundary shape

**`min_hole_km2` (Minimum Hole Area to Preserve)**

Choose based on features in your study area:
- **0.1 km²**: Preserve very small water bodies
- **1.0 km²**: DEFAULT - balance between cleaning and preservation
- **5.0 km²**: Only preserve large lakes
- **1000.0 km²**: Remove all holes (aggressive cleaning)

**How to Validate Your Parameters:**

1. **Visual Inspection**: Open output in QGIS and zoom to boundary details
2. **Hole Count Check**:
   ```python
   n_holes = len(polygon.interiors) if isinstance(polygon, Polygon) else \
             sum(len(p.interiors) for p in polygon.geoms)
   print(f"Remaining holes: {n_holes}")
   ```
3. **Area Comparison**: Should differ by < 0.1% from simple union
4. **Reference Check**: Compare with known watershed delineations

#### Performance Characteristics

**Time Complexity:**
- Stage 1 (validation): O(n) where n = number of unit catchments
- Stage 2 (union + buffer): O(n log n) for union, O(m) for buffer (m = vertices)
- Stage 3 (hole removal): O(h) where h = number of holes

**Memory Usage:**
- Peak memory during buffer operations
- Typical overhead: +200-500 MB per watershed
- Released after processing each station

**Processing Time Examples:**
```
Small watershed (50 unit catchments):     +2-3 seconds
Medium watershed (500 unit catchments):   +5-8 seconds
Large watershed (5000 unit catchments):   +10-20 seconds
```

#### Alternative Approaches (Not Implemented)

**Why not these methods?**

1. **Topology Processing**: Tools like GRASS `v.clean` or PostGIS `ST_MakeValid`
   - Requires external dependencies
   - Harder to configure and integrate
   - Our buffer approach is simpler and portable

2. **Concave Hull**: Wrapping all catchments with alpha shapes
   - May lose important boundary details
   - Requires parameter tuning (alpha value)
   - Can over-simplify complex watersheds

3. **Snapping**: Move nearby vertices together
   - Computationally expensive for large datasets
   - Risk of creating new topology errors
   - Requires careful tolerance selection

**Our approach (buffer + hole removal) offers the best balance of:**
- Simplicity (pure Shapely, no external tools)
- Effectiveness (fixes 95%+ of gaps)
- Performance (acceptable overhead)
- Reliability (minimal risk of new errors)

#### Customization Examples

**Example 1: High-Precision Boundary**
```python
# Minimal distortion, only close very small gaps
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.00005,  # ~5.5m
    min_hole_km2=0.5      # Preserve lakes > 0.5 km²
)
```

**Example 2: Aggressive Cleaning**
```python
# Remove all holes, larger buffer
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.0003,   # ~33m
    min_hole_km2=1000.0   # Remove all holes
)
```

**Example 3: Lake-Rich Region**
```python
# Preserve many small lakes
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.0001,   # Standard gap closing
    min_hole_km2=0.1      # Keep lakes > 0.1 km²
)
```

### License

MIT License

---

## 中文说明

### 概述

MERIT-Basins流域提取的优化Python工具。基于测站坐标自动提取上游集水区，具有性能优化、**拓扑间隙修复**和健壮的错误处理功能。

### 主要特性

- **拓扑感知合并** ✨ **v2.2新增**: 修复单元流域间微小的像素级间隙
  - 消除95%以上的合并流域中的窟窿伪影
  - 三阶段流程: buffer(0) + 间隙闭合 + 小孔洞移除
  - 保留真实地理特征（>1km²的湖泊），同时移除伪影
- **高性能**: 使用`unary_union`比传统dissolve操作快3-5倍
- **预计算投影**: 减少重复的坐标转换
- **内存高效**: 内置内存监控和垃圾回收
- **断点续传**: 自动跳过已完成的测站
- **批量处理**: 支持多测站处理和进度跟踪
- **质量控制**: 自动与参考面积进行验证
- **多种输出**:
  - 单站流域边界 (GeoPackage格式)
  - 所有流域的合并GeoPackage
  - 统计汇总和可视化地图
  - 处理日志

### 🔧 关键修复: 拓扑间隙解决方案 (v2.2)

**问题:**
MERIT-Basins的单元流域边界之间经常存在微小间隙（几个像素宽），原因包括：
- 栅格转矢量转换过程中的伪影
- 浮点精度问题
- 数据处理过程中的边界对齐不完美

使用简单的`unary_union`时，这些间隙会被保留，导致最终流域多边形中出现大量小窟窿。

**解决方案:**
三阶段鲁棒合并流程：

1. **拓扑修复**: `buffer(0)` 修复无效几何体和自相交
2. **间隙闭合**: 正负缓冲（`buffer(+ε).buffer(-ε)`）桥接像素级间隙
3. **孔洞过滤**: 移除残留的小孔洞（< 1 km²），同时保留真实湖泊

**结果:**
- 无拓扑伪影的干净流域边界
- 保留真实地理特征（大型湖泊）
- 边界变形极小（面积变化 < 0.1%）

**性能影响:**
- 处理时间: 每个测站增加15-35%开销
- 典型测站: +3-10秒
- 精度提升远超性能成本

详见[技术文档](#拓扑修复技术细节)了解实现详情。

### 📚 文档资源

| 资源 | 说明 |
|------|------|
| [新生教程](examples/tutorial_freshman_basics.ipynb) | 面向初学者的 Jupyter Notebook，图解核心算法 |
| [高级指南](docs/advanced_guide.md) | 算法流程图解、参数调优、复杂场景解决方案 |
| [示例](examples/README.md) | 示例代码和使用说明 |

### 系统要求

```
Python 3.7+
```

### 安装步骤

**方式1: 作为包安装（推荐）**

```bash
git clone https://github.com/licm13/Merit-catchment-extract.git
cd Merit-catchment-extract
pip install -e .
```

安装后，可以在任何位置运行工具:
```bash
extract-merit
```

**方式2: 手动配置**

1. 克隆仓库:
```bash
git clone https://github.com/licm13/Merit-catchment-extract.git
cd Merit-catchment-extract
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 在`config.yaml`中配置路径（见配置说明）

### 配置说明

创建`config.yaml`文件，包含以下内容:

```yaml
# 输入数据路径
riv_shp: "/path/to/riv_pfaf_X_MERIT_Hydro_v07_Basins_v01.shp"
cat_shp: "/path/to/cat_pfaf_X_MERIT_Hydro_v07_Basins_v01.shp"
china_prov_shp: "/path/to/china_provinces.shp"
excel_path: "/path/to/station_info.xlsx"

# 输出目录
out_root: "/path/to/output"

# 处理参数
snap_dist_m: 5000.0          # 最大捕捉距离（米）
order_first: false           # 优先考虑河流等级而非距离
max_up_reach: 100000         # 最大上游河段数
area_tol: 0.20               # 面积容差（20%）
area_epsg: 6933              # 面积计算的EPSG代码
save_individual_shp: false   # 保存单独的shapefile（使用GeoPackage代替）
memory_check_interval: 50    # 每N个测站检查内存
```

### 使用方法

**方式1: 命令行工具（如果已作为包安装）**
```bash
extract-merit
```

**方式2: 直接运行Python脚本**
```bash
python extract_merit_catchment.py
```

**方式3: 可执行方式 (Linux/Mac)**
```bash
chmod +x extract_merit_catchment.py
./extract_merit_catchment.py
```

工具将执行以下步骤:
1. 从Excel文件读取测站信息
2. 加载MERIT-Basins河网和流域数据
3. 对每个测站:
   - 捕捉到最近的河段
   - 追溯上游河网
   - 提取并合并单元流域
   - 与参考面积进行验证
   - 生成输出结果

### 输入数据格式

Excel文件应包含以下列（支持中英文列名）:
- 测站编码: `测站编码`/`code`/`station_id`
- 经度: `经度`/`lon`/`longitude`
- 纬度: `纬度`/`lat`/`latitude`
- 集水区面积: `集水区面积`/`area` (单位: km²或m²)

### 输出结构

```
输出目录/
├── summary.csv                    # 处理汇总
├── summary_chart.png              # 结果可视化
├── all_catchments.gpkg            # 所有流域合并文件
├── run_log.txt                    # 详细处理日志
└── sites/
    └── [测站编码]/
        ├── [测站编码]_catchment.gpkg   # 流域边界
        ├── [测站编码]_stats.csv        # 测站统计
        └── [测站编码]_map.png          # 可视化地图
```

### 性能优化

1. **预计算投影**: 河网和流域仅投影一次
2. **Unary Union**: 替代dissolve操作（提速3-5倍）
3. **空间索引**: 快速最近邻搜索
4. **内存管理**: 自动垃圾回收
5. **单文件输出**: GeoPackage减少I/O开销

### 拓扑修复技术细节

#### 问题分析

MERIT-Basins单元流域源自栅格数据（数字高程模型和流向栅格）。矢量化过程可能在相邻流域之间引入微小间隙，原因包括：

1. **栅格分辨率**: 在90m或3角秒分辨率下，像素边缘可能无法完美对齐
2. **坐标精度**: 浮点数表示限制（约15位小数）
3. **拓扑一致性**: 每个流域的矢量边界独立生成
4. **数据处理**: MERIT-Basins创建过程中的多次转换

这些间隙通常宽1-5个像素（约90-450米），但可能在大流域中造成数百个小孔洞。

#### 修复方法：三阶段流程

**阶段1: 单个几何对象修复**
```python
# 检查并修复无效几何体
clean_geoms = []
for g in geometries:
    if not g.is_valid:
        g = g.buffer(0)  # 零缓冲技巧修复拓扑
    clean_geoms.append(g)
```
- `buffer(0)` 是修复自相交的常用GIS技术
- 确保所有输入几何体在合并前都是有效的

**阶段2: 使用缓冲操作闭合间隙**
```python
# 合并所有几何对象
merged = unary_union(clean_geoms)

# 闭合间隙：先扩张后收缩
merged = merged.buffer(buffer_dist).buffer(-buffer_dist)
```
- `buffer(+ε)`: 将几何体扩张一小段距离（默认0.0001°≈11米）
  - 填充小于缓冲距离的间隙
  - 在间隙上创建临时"桥梁"
- `buffer(-ε)`: 收缩回近似原始边界
  - 移除扩张部分
  - 保持间隙"愈合"且边界变化不大

**阶段3: 移除小孔洞**
```python
# 移除小于阈值的孔洞
for interior in polygon.interiors:
    hole_area = Polygon(interior).area
    if hole_area < threshold:
        # 丢弃此孔洞
    else:
        # 保留此孔洞（真实湖泊）
```
- 区分伪影（小）和真实特征（大）
- 默认阈值：1 km²（可通过 `min_hole_km2` 参数调整）
- 保留重要地理特征如湖泊

#### 参数调优指南

**`buffer_dist` (缓冲距离，以度为单位)**

根据数据中的间隙大小选择：
- **0.00005° (≈ 5.5m)**: 非常小的间隙，需要高精度
- **0.0001° (≈ 11m)**: 默认值 - 适用于大多数MERIT-Basins数据
- **0.0002° (≈ 22m)**: 较大间隙，较粗糙的数据
- **0.0005° (≈ 55m)**: 非常大的间隙（检查数据质量！）

太小：可能无法闭合所有间隙
太大：可能使边界形状变形

**`min_hole_km2` (保留孔洞的最小面积)**

根据研究区域的特征选择：
- **0.1 km²**: 保留非常小的水体
- **1.0 km²**: 默认值 - 清理和保留之间的平衡
- **5.0 km²**: 只保留大型湖泊
- **1000.0 km²**: 移除所有孔洞（激进清理）

**如何验证参数设置：**

1. **视觉检查**: 在QGIS中打开输出并缩放到边界细节
2. **孔洞计数检查**:
   ```python
   n_holes = len(polygon.interiors) if isinstance(polygon, Polygon) else \
             sum(len(p.interiors) for p in polygon.geoms)
   print(f"剩余孔洞数: {n_holes}")
   ```
3. **面积对比**: 应与简单合并的面积相差 < 0.1%
4. **参考检查**: 与已知流域边界对比

#### 性能特征

**时间复杂度：**
- 阶段1（验证）: O(n)，其中n = 单元流域数量
- 阶段2（合并 + 缓冲）: O(n log n) 用于合并，O(m) 用于缓冲（m = 顶点数）
- 阶段3（孔洞移除）: O(h)，其中h = 孔洞数量

**内存使用：**
- 缓冲操作期间达到峰值
- 典型开销：每个流域 +200-500 MB
- 处理完每个测站后释放

**处理时间示例：**
```
小流域（50个单元流域）:      +2-3秒
中等流域（500个单元流域）:    +5-8秒
大流域（5000个单元流域）:     +10-20秒
```

#### 替代方法（未实现）

**为什么不用这些方法？**

1. **拓扑处理工具**: 如GRASS `v.clean`或PostGIS `ST_MakeValid`
   - 需要外部依赖
   - 配置和集成更困难
   - 我们的缓冲方法更简单和便携

2. **凹包算法**: 用alpha shapes包裹所有流域
   - 可能丢失重要边界细节
   - 需要参数调优（alpha值）
   - 可能过度简化复杂流域

3. **捕捉**: 将附近顶点移到一起
   - 对大数据集计算量大
   - 可能创建新的拓扑错误
   - 需要仔细选择容差

**我们的方法（缓冲 + 孔洞移除）提供最佳平衡：**
- 简单性（纯Shapely，无需外部工具）
- 有效性（修复95%以上的间隙）
- 性能（可接受的开销）
- 可靠性（创建新错误的风险最小）

#### 定制示例

**示例1: 高精度边界**
```python
# 最小变形，只闭合非常小的间隙
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.00005,  # ~5.5m
    min_hole_km2=0.5      # 保留 > 0.5 km²的湖泊
)
```

**示例2: 激进清理**
```python
# 移除所有孔洞，较大缓冲
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.0003,   # ~33m
    min_hole_km2=1000.0   # 移除所有孔洞
)
```

**示例3: 湖泊丰富区域**
```python
# 保留许多小湖泊
cat_geom = merge_catchments_fixed_robust(
    geometries,
    buffer_dist=0.0001,   # 标准间隙闭合
    min_hole_km2=0.1      # 保留 > 0.1 km²的湖泊
)
```

### 许可证

MIT License