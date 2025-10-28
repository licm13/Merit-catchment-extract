# MERIT-Basins Watershed Extraction Tool

[中文](#中文说明) | [English](#english)

---

## English

### Overview

An optimized Python tool for extracting watersheds from MERIT-Basins hydrological dataset. This tool automatically delineates upstream catchment areas for gauging stations based on their coordinates, with performance optimizations and robust error handling.

### Key Features

- **High Performance**: 3-5x faster than traditional dissolve operations using `unary_union`
- **Pre-computed Projections**: Reduces redundant coordinate transformations
- **Memory Efficient**: Built-in memory monitoring and garbage collection
- **Resume Capability**: Automatically skips completed stations
- **Batch Processing**: Process multiple stations with progress tracking
- **Quality Control**: Automatic area validation against reference data
- **Multiple Outputs**:
  - Individual catchment boundaries (GeoPackage)
  - Consolidated GeoPackage with all catchments
  - Statistical summaries and visualization maps
  - Processing logs

### Prerequisites

```
Python 3.7+
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Merit-catchment-extract.git
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

```bash
python Extract_Merit
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

### License

MIT License

---

## 中文说明

### 概述

MERIT-Basins流域提取的优化Python工具。基于测站坐标自动提取上游集水区，具有性能优化和健壮的错误处理功能。

### 主要特性

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

### 系统要求

```
Python 3.7+
```

### 安装步骤

1. 克隆仓库:
```bash
git clone https://github.com/yourusername/Merit-catchment-extract.git
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

```bash
python Extract_Merit
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

### 许可证

MIT License