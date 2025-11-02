# -*- coding: utf-8 -*-
"""
输入输出管理模块
Input/Output Management Module

本模块负责配置文件加载、Excel数据读取、面积单位归一化等I/O相关操作。
This module handles configuration loading, Excel data reading, area unit normalization, and other I/O operations.
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
import yaml


# ========= 默认配置常量 (Default Configuration Constants) =========

DEFAULT_SNAP_DISTANCE_M = 5000.0      # 捕捉距离(米)
DEFAULT_MAX_UPSTREAM_REACHES = 100000  # 最大上游河段数
DEFAULT_AREA_TOLERANCE = 0.20         # 面积相对误差容忍度(20%)
DEFAULT_AREA_EPSG = 6933             # 面积计算投影坐标系(等面积投影)
DEFAULT_DISTANCE_EPSG = 3857         # 距离计算投影坐标系(Web墨卡托)
DEFAULT_MEMORY_CHECK_INTERVAL = 50   # 内存检查间隔(处理多少个站点)
AREA_UNIT_THRESHOLD = 1e6            # 面积单位转换阈值(用于判断单位是km²还是m²)


# ========= 配置文件管理 (Configuration File Management) =========

def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件(优先使用config.yaml,否则使用默认值)
    Load configuration file (prioritize config.yaml, otherwise use defaults)

    功能说明:
    --------
    该函数实现灵活的配置管理机制,支持YAML配置文件和硬编码默认值的组合。
    这种设计允许用户在不修改代码的情况下定制工具行为,同时确保即使没有
    配置文件也能正常运行。

    工作原理 (How It Works):
    -----------------------
    1. 定义完整的默认配置字典,包含所有必需参数
    2. 检查config.yaml是否存在于脚本目录
    3. 如果找到,尝试加载YAML文件(需要PyYAML包)
    4. 用户配置与默认配置合并(用户值覆盖默认值)
    5. 返回完整的配置字典

    配置优先级 (Configuration Priority):
    ----------------------------------
    1. 用户提供的config.yaml(最高优先级)
    2. 脚本内的默认配置
    3. 模块级常量定义的默认值

    配置文件结构建议 (Recommended Configuration Structure):
    --------------------------------------------------
    ```yaml
    # 路径配置 (Path Configuration)
    riv_shp: "/path/to/river_network.shp"
    cat_shp: "/path/to/catchments.shp"
    china_prov_shp: "/path/to/provinces.shp"
    excel_path: "/path/to/stations.xlsx"
    out_root: "/path/to/output"

    # 算法参数配置 (Algorithm Parameters)
    snap_dist_m: 5000.0        # 捕捉距离
    order_first: false         # 是否优先按河流等级选择
    max_up_reach: 100000       # 最大上游河段数
    area_tol: 0.20             # 面积容忍度
    area_epsg: 6933            # 面积计算投影

    # 输出配置 (Output Configuration)
    save_individual_shp: false # 是否保存单站shapefile
    memory_check_interval: 50  # 内存检查间隔
    ```

    参数说明与调优建议 (Parameter Description and Tuning):
    ---------------------------------------------------
    **snap_dist_m** (捕捉距离):
    - 默认: 5000米(5公里)
    - 含义: 搜索最近河段的最大距离
    - 调优: 山区河网稀疏时可增至10000-15000
            平原河网密集时可减至2000-3000

    **order_first** (河流等级优先):
    - 默认: false(优先最近距离)
    - true: 优先选择高等级河流(主河道)
    - false: 优先选择最近距离的河段
    - 调优: 主干流站点建议true,支流站点建议false

    **max_up_reach** (最大上游河段数):
    - 默认: 100000
    - 含义: 上游网络规模上限,防止处理超大流域
    - 调优: 全球大河(如长江)可增至200000-500000
            小流域可减至10000-50000以加快处理

    **area_tol** (面积容忍度):
    - 默认: 0.20(20%)
    - 含义: 计算面积与参考面积的允许相对误差
    - 调优: 高精度需求时减至0.10(10%)
            粗略验证时增至0.30-0.50

    **area_epsg** (面积计算投影):
    - 默认: 6933(Equal Earth等面积投影)
    - 备选: 3857(Web Mercator,速度快但精度略低)
            自定义区域等面积投影
    - 调优: 全球尺度用6933,区域尺度可用当地UTM投影

    为什么使用YAML而非JSON/INI (Why YAML over JSON/INI):
    -------------------------------------------------
    - YAML支持注释,便于文档化配置
    - 语法简洁,无需大量引号和逗号
    - 支持多种数据类型(字符串、数字、布尔、列表等)
    - Python生态系统广泛支持

    Args:
        config_path (str, optional): 配置文件路径。如为None,自动查找脚本目录下的config.yaml
                                     Configuration file path. If None, auto-search config.yaml in script directory

    Returns:
        Dict[str, Any]: 配置字典,包含所有必需的参数
                       Configuration dictionary with all required parameters
            Keys:
            - riv_shp (str): 河网shapefile路径
            - cat_shp (str): 单元流域shapefile路径
            - china_prov_shp (str): 省界shapefile路径
            - excel_path (str): 测站信息Excel路径
            - out_root (str): 输出根目录
            - snap_dist_m (float): 捕捉距离(米)
            - order_first (bool): 是否优先按河流等级捕捉
            - max_up_reach (int): 最大上游河段数限制
            - area_tol (float): 面积相对误差容忍度
            - area_epsg (int): 面积计算EPSG代码
            - save_individual_shp (bool): 是否保存单站shapefile
            - memory_check_interval (int): 内存检查间隔

    故障排除 (Troubleshooting):
    -------------------------
    问题: 配置文件加载失败
    解决: 检查YAML语法(缩进、冒号后空格等)
         确保PyYAML已安装: pip install pyyaml

    问题: 路径配置不生效
    解决: 使用绝对路径而非相对路径
         Windows路径使用正斜杠或双反斜杠
         检查路径中的空格和特殊字符

    问题: 参数类型错误
    解决: 确保数字不加引号(5000而非"5000")
         布尔值用true/false(小写)

    Example:
        >>> config = load_config()
        ✓ 已加载配置文件: /path/to/config.yaml
        >>> print(config['snap_dist_m'])
        5000.0

        >>> # 无配置文件时使用默认值
        >>> config = load_config()
        ℹ 未找到config.yaml,使用默认配置
        >>> print(config['area_epsg'])
        6933
    """
    # 默认配置(如果没有找到config.yaml,将使用这些值)
    config = {
        # ========= 路径配置 (Path Configuration) =========
        'riv_shp': r"Z:\Topography\MERIT-Basins\MERIT_Hydro_v07_Basins_v01\pfaf_level_01\pfaf_4_MERIT_Hydro_v07_Basins_v01\riv_pfaf_4_MERIT_Hydro_v07_Basins_v01.shp",
        'cat_shp': r"Z:\Topography\MERIT-Basins\MERIT_Hydro_v07_Basins_v01\pfaf_level_01\pfaf_4_MERIT_Hydro_v07_Basins_v01\cat_pfaf_4_MERIT_Hydro_v07_Basins_v01.shp",
        'china_prov_shp': r"Z:\ARCGIS_Useful_data\China\中国行政区_包含沿海岛屿.shp",
        'excel_path': r"Z:\Runoff_Flood\China_runoff\流域基础信息\水文站信息.xlsx",
        'out_root': r"Z:\Runoff_Flood\China_runoff\流域基础信息\流域面积",

        # ========= 算法参数配置 (Algorithm Parameters) =========
        'snap_dist_m': DEFAULT_SNAP_DISTANCE_M,
        'order_first': False,
        'max_up_reach': DEFAULT_MAX_UPSTREAM_REACHES,
        'area_tol': DEFAULT_AREA_TOLERANCE,
        'area_epsg': DEFAULT_AREA_EPSG,

        # ========= 输出配置 (Output Configuration) =========
        'save_individual_shp': False,
        'memory_check_interval': DEFAULT_MEMORY_CHECK_INTERVAL
    }

    # 确定配置文件路径
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__) or '.', 'config.yaml')

    # 尝试加载YAML配置文件
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config.update(user_config)
                    print(f"✓ 已加载配置文件: {config_path}")
        except ImportError:
            print("⚠ 未安装PyYAML,使用默认配置。安装: pip install pyyaml")
        except Exception as e:
            print(f"⚠ 配置文件加载失败,使用默认配置: {e}")
    else:
        print(f"ℹ 未找到config.yaml,使用默认配置")

    return config


# ========= Excel数据读取 (Excel Data Reading) =========

def read_site_info(xlsx_path: str) -> Tuple[str, pd.DataFrame]:
    """
    从Excel文件读取测站信息
    Read station information from Excel file

    功能说明:
    --------
    该函数实现智能的Excel解析,能够自动识别中英文列名,灵活处理不同格式的
    测站信息表。这种设计最大化了对各种数据源的兼容性,减少用户的数据准备工作。

    工作原理 (How It Works):
    -----------------------
    1. 读取Excel工作簿中的所有工作表
    2. 对每个工作表,标准化列名(去除首尾空格)
    3. 使用候选列名列表搜索必需字段:
       - 测站编码: 支持"测站编码"、"测站代码"、"站码"、"code"等
       - 经度: 支持"经度"、"lon"、"longitude"等
       - 纬度: 支持"纬度"、"lat"、"latitude"等
       - 面积: 支持"集水区面积"、"面积"、"area"等
    4. 找到第一个包含所有必需字段的工作表
    5. 提取数据并进行清洗和验证

    为什么支持多语言列名 (Why Multi-language Column Support):
    -----------------------------------------------------
    - 中国用户常用中文列名
    - 国际用户习惯英文列名
    - 不同数据源格式不统一
    - 自动识别减少人工干预

    数据清洗流程 (Data Cleaning Workflow):
    ------------------------------------
    1. 列名标准化: 去除空格,统一大小写
    2. 编码转换: 转为字符串并去除首尾空格
    3. 坐标验证: 转为数值类型,无效值转为NaN
    4. 面积验证: 转为数值类型,无效值转为NaN
    5. 缺失值过滤: 删除编码、经度、纬度任一缺失的行

    参数调优建议 (Parameter Tuning):
    ------------------------------
    如需支持更多列名变体,可修改候选列表:
    ```python
    cand_code = ["测站编码", "测站代码", "站码", "站号", "code",
                 "station_id", "site_code", "gauge_id"]
    cand_lon = ["经度", "lon", "longitude", "long", "x", "东经"]
    cand_lat = ["纬度", "lat", "latitude", "y", "北纬"]
    cand_area = ["集水区面积", "面积", "area", "catchment_area",
                 "drainage_area", "watershed_area"]
    ```

    Args:
        xlsx_path (str): Excel文件路径(支持.xlsx和.xls格式)
                        Excel file path (supports .xlsx and .xls)

    Returns:
        Tuple[str, pd.DataFrame]: (工作表名称, 测站信息数据框)
                                 (Sheet name, Station information DataFrame)
            DataFrame包含以下列:
            - code: 测站编码(字符串)
            - lon: 经度(浮点数)
            - lat: 纬度(浮点数)
            - area: 集水区面积(浮点数,单位可能是km²或m²)

    Raises:
        RuntimeError: 如果所有工作表都不包含必需的字段组合
                     If no sheet contains all required fields

    数据质量检查建议 (Data Quality Checks):
    ------------------------------------
    读取数据后,建议执行以下检查:
    ```python
    sheet, df = read_site_info("stations.xlsx")

    # 检查坐标范围(中国区域)
    assert df['lon'].between(73, 136).all(), "经度超出中国范围"
    assert df['lat'].between(18, 54).all(), "纬度超出中国范围"

    # 检查面积合理性
    assert (df['area'] > 0).all(), "存在负面积或零面积"
    assert df['area'].max() < 2000000, "面积异常大(可能单位错误)"

    # 检查重复站点
    duplicates = df[df.duplicated(subset=['code'], keep=False)]
    if not duplicates.empty:
        print(f"警告: 发现{len(duplicates)}个重复站点")
    ```

    故障排除 (Troubleshooting):
    -------------------------
    问题: RuntimeError未找到包含所有字段的工作表
    解决: 1. 检查Excel文件是否包含必需字段
         2. 确认列名拼写正确
         3. 检查是否有隐藏列或合并单元格
         4. 尝试手动重命名列为标准名称

    问题: 读取的数据量少于预期
    解决: 检查是否有空行或缺失值导致行被过滤
         查看原始Excel是否有数据格式问题

    问题: 编码问题(中文乱码)
    解决: 确保Excel文件保存为UTF-8编码
         尝试在Excel中另存为新文件

    Example:
        >>> sheet, df = read_site_info("water_stations.xlsx")
        >>> print(f"从工作表 '{sheet}' 读取 {len(df)} 个站点")
        从工作表 'Sheet1' 读取 125 个站点
        >>> print(df.head())
          code        lon       lat      area
        0  60101  110.536  35.231   5000.0
        1  60102  111.234  36.567   8500.0
        ...
    """
    # 定义列名候选(支持中英文多种表达)
    cand_code = ["测站编码", "测站代码", "站码", "站号", "code", "station_id"]
    cand_lon = ["经度", "lon", "longitude"]
    cand_lat = ["纬度", "lat", "latitude"]
    cand_area = ["集水区面积", "面积", "area"]

    # 读取所有工作表
    book = pd.read_excel(xlsx_path, sheet_name=None)

    # 遍历所有工作表,找到第一个包含所有必需字段的
    for sheet_name, df in book.items():
        # 标准化列名(去除首尾空格)
        cols = {str(c).strip(): c for c in df.columns}

        # 搜索匹配的列
        code_col = next((cols[c] for c in cols if c in cand_code), None)
        lon_col = next((cols[c] for c in cols if c in cand_lon), None)
        lat_col = next((cols[c] for c in cols if c in cand_lat), None)
        area_col = next((cols[c] for c in cols if c in cand_area), None)

        # 如果找到所有必需列,进行数据清洗并返回
        if code_col and lon_col and lat_col and area_col:
            # 提取相关列
            out = df[[code_col, lon_col, lat_col, area_col]].copy()
            out.columns = ["code", "lon", "lat", "area"]

            # 数据清洗
            out["code"] = out["code"].astype(str).str.strip()
            out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
            out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
            out["area"] = pd.to_numeric(out["area"], errors="coerce")

            # 过滤缺失值并返回
            return sheet_name, out.dropna(subset=["code", "lon", "lat"])

    # 未找到合适的工作表,抛出错误
    raise RuntimeError(
        "未在Excel中找到同时包含【测站编码/经度/纬度/集水区面积】的工作表。\n"
        "请检查Excel文件是否包含这些列(支持中英文列名)。"
    )


# ========= 面积单位归一化 (Area Unit Normalization) =========

def normalize_area_to_m2(series_area: pd.Series) -> pd.Series:
    """
    将面积数据归一化为平方米
    Normalize area data to square meters

    功能说明:
    --------
    自动检测面积数据的单位(km²或m²)并统一转换为m²,避免单位混淆导致的
    计算错误。这是数据预处理的关键步骤,确保后续面积比较和验证的一致性。

    工作原理 (How It Works):
    -----------------------
    1. 过滤掉空值(NaN, None等)
    2. 计算非空值的中位数
    3. 根据中位数判断单位:
       - 中位数 < 1,000,000: 推断为km²,乘以1,000,000转为m²
       - 中位数 >= 1,000,000: 推断为m²,无需转换
    4. 返回统一单位的序列

    为什么使用中位数而非平均值 (Why Median over Mean):
    -----------------------------------------------
    - 中位数对异常值不敏感
    - 避免极大或极小值影响单位判断
    - 更稳健的统计量

    单位判断逻辑说明 (Unit Detection Logic):
    -------------------------------------
    阈值设为1,000,000的原理:
    - 1 km² = 1,000,000 m²
    - 如果面积值普遍小于1,000,000,很可能是km²
    - 如果面积值普遍大于1,000,000,很可能是m²

    示例:
    - 流域面积1500 km² → 中位数≈1500 → 小于阈值 → 判断为km² → 转换为1,500,000,000 m²
    - 流域面积1500000000 m² → 中位数≈1500000000 → 大于阈值 → 判断为m² → 无需转换

    边界情况处理 (Edge Cases):
    -------------------------
    1. 全为空值: 返回原序列(全NaN)
    2. 中位数接近阈值: 可能误判,建议手动检查
    3. 混合单位: 无法自动处理,需要数据清洗

    参数调优建议 (Parameter Tuning):
    ------------------------------
    如果数据集中的流域都很小(如小于100 km²),可能需要调整阈值:
    ```python
    # 对于小流域数据集
    threshold = 500_000  # 0.5 km²
    if median_val < threshold:
        return series_area * 1_000_000.0
    ```

    Args:
        series_area (pd.Series): 面积数据序列(可能是km²或m²单位)
                                Area data series (possibly in km² or m²)

    Returns:
        pd.Series: 归一化为平方米的面积序列
                  Area series normalized to square meters

    数据验证建议 (Data Validation):
    -----------------------------
    转换后建议验证:
    ```python
    areas_m2 = normalize_area_to_m2(df['area'])

    # 检查合理范围(1 km²到1,000,000 km²)
    assert (areas_m2 >= 1e6).all(), "存在小于1km²的流域"
    assert (areas_m2 <= 1e12).all(), "存在大于1,000,000km²的流域"

    # 打印统计信息
    print(f"面积范围: {areas_m2.min()/1e6:.2f} - {areas_m2.max()/1e6:.2f} km²")
    print(f"平均面积: {areas_m2.mean()/1e6:.2f} km²")
    ```

    Example:
        >>> # 示例1: km²单位数据
        >>> areas_km2 = pd.Series([1500, 2000, 2500, 3000])
        >>> areas_m2 = normalize_area_to_m2(areas_km2)
        >>> print(areas_m2)
        0    1500000000.0
        1    2000000000.0
        2    2500000000.0
        3    3000000000.0
        dtype: float64

        >>> # 示例2: m²单位数据(无需转换)
        >>> areas_m2_input = pd.Series([1500000000, 2000000000])
        >>> areas_m2 = normalize_area_to_m2(areas_m2_input)
        >>> print(areas_m2)
        0    1500000000.0
        1    2000000000.0
        dtype: float64

        >>> # 示例3: 包含空值
        >>> areas_with_nan = pd.Series([1500, None, 2500])
        >>> areas_m2 = normalize_area_to_m2(areas_with_nan)
        >>> print(areas_m2)
        0    1500000000.0
        1             NaN
        2    2500000000.0
        dtype: float64
    """
    # 过滤空值
    s = series_area.dropna()
    if s.empty:
        return series_area

    # 根据中位数判断单位
    median_val = float(s.median())
    if median_val < AREA_UNIT_THRESHOLD:
        # 推断为km²,转换为m²
        return series_area * 1_000_000.0
    else:
        # 已是m²
        return series_area
