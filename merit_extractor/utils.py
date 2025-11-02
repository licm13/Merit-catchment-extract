# -*- coding: utf-8 -*-
"""
通用工具函数模块
Common Utility Functions Module

本模块包含日志记录、格式化、内存管理和坐标系转换等通用工具函数。
This module contains general utilities for logging, formatting, memory management, and CRS handling.
"""

import os
import sys
import time
from typing import Any, Optional
import geopandas as gpd


# ========= 常量定义 (Constants) =========
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MEMORY_THRESHOLD = 85.0  # 内存使用率警戒线(%)


# ========= 日志管理 (Logging Management) =========

def log(msg: str, log_file: Optional[str] = None) -> None:
    """
    记录日志到控制台和文件
    Log messages to console and file

    功能说明:
    --------
    该函数实现统一的日志记录机制,确保所有重要事件都被记录下来以供后续分析。
    自动添加时间戳,并同时输出到控制台和日志文件,方便实时监控和事后审查。

    工作原理 (How It Works):
    -----------------------
    1. 获取当前时间戳,格式化为可读形式
    2. 将消息与时间戳组合成日志行
    3. 输出到标准输出(控制台)并立即刷新缓冲区
    4. 如果提供了日志文件路径,追加写入文件

    Args:
        msg (str): 日志消息内容
                  Log message content
        log_file (Optional[str]): 日志文件路径(可选)
                                 Log file path (optional)

    使用场景 (Use Cases):
    --------------------
    - 记录处理进度: log(f"正在处理第{i}个站点")
    - 记录错误信息: log(f"错误: {error_message}")
    - 记录性能指标: log(f"处理耗时: {elapsed:.2f}秒")
    - 记录配置信息: log(f"使用配置: {config_path}")

    注意事项 (Notes):
    ----------------
    - 立即刷新输出缓冲区确保日志实时显示
    - 文件写入使用追加模式,不会覆盖已有日志
    - UTF-8编码确保中文等字符正确显示
    - 线程安全性:在多线程环境下可能需要额外的锁机制

    Example:
        >>> log("开始处理站点", "/path/to/run_log.txt")
        [2025-10-28 10:30:45] 开始处理站点
    """
    timestamp = time.strftime(TIME_FORMAT)
    line = f"[{timestamp}] {msg}"

    # 输出到控制台
    print(line)
    sys.stdout.flush()

    # 写入日志文件
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def fmt_pct(x: Optional[float]) -> str:
    """
    格式化百分比显示
    Format percentage for display

    功能说明:
    --------
    将小数形式的比率转换为易读的百分比字符串,统一输出格式。
    This function converts decimal ratios to readable percentage strings with consistent formatting.

    工作原理 (How It Works):
    -----------------------
    1. 检查输入是否可以转换为浮点数
    2. 如果有效,格式化为百分比字符串(保留1位小数)
    3. 如果无效(None, NaN等),返回"NA"表示数据缺失

    参数调优建议 (Parameter Tuning):
    ------------------------------
    - 当前保留1位小数(如15.0%),适用于大多数场景
    - 如需更高精度,可修改为 f"{float(x):.2%}" (如15.03%)
    - 如需更简洁,可修改为 f"{float(x):.0%}" (如15%)

    Args:
        x (Optional[float]): 小数值(如0.15表示15%)
                            Decimal value (e.g., 0.15 for 15%)

    Returns:
        str: 格式化的百分比字符串(如"15.0%")或"NA"(如果输入无效)
            Formatted percentage string or "NA" if invalid

    Example:
        >>> fmt_pct(0.1234)
        '12.3%'
        >>> fmt_pct(None)
        'NA'
        >>> fmt_pct(0.0567)
        '5.7%'
    """
    try:
        return f"{float(x):.1%}"
    except (TypeError, ValueError):
        return "NA"


# ========= 内存管理 (Memory Management) =========

def check_memory(threshold: float = DEFAULT_MEMORY_THRESHOLD) -> bool:
    """
    检查内存使用情况,必要时触发垃圾回收
    Check memory usage and trigger garbage collection if needed

    功能说明:
    --------
    监控系统内存使用率,当超过警戒线时自动执行垃圾回收,防止内存溢出。
    这对于长时间运行的批处理任务至关重要,可避免因内存不足导致程序崩溃。

    工作原理 (How It Works):
    -----------------------
    1. 尝试导入psutil库获取系统内存信息
    2. 检查当前内存使用百分比
    3. 如果超过阈值,记录警告并执行gc.collect()
    4. 如果psutil未安装,静默跳过检查

    为什么需要这个功能 (Why This is Needed):
    -------------------------------------
    - Python的垃圾回收器不总是立即释放内存
    - 处理大型GIS数据会产生大量临时对象
    - 批处理数百个站点时内存会逐渐累积
    - 主动回收可避免操作系统内存交换(swap)导致的性能下降

    内存管理策略 (Memory Management Strategy):
    ----------------------------------------
    1. 定期检查(如每50个站点)
    2. 超过阈值时主动回收
    3. 大对象处理后显式del和gc.collect()
    4. 使用生成器而非列表减少内存峰值

    Args:
        threshold (float): 内存使用率阈值(百分比),默认85%
                          Memory usage threshold (percentage), default 85%

    Returns:
        bool: 如果执行了垃圾回收返回True,否则返回False
             True if garbage collection was triggered, False otherwise

    故障排除 (Troubleshooting):
    -------------------------
    问题: 频繁触发垃圾回收,影响性能
    解决: 增大threshold到90-95%,或减少检查频率

    问题: 内存仍然不断增长
    解决: 检查是否有内存泄漏(未释放的大对象引用)

    问题: psutil未安装导致无法监控
    解决: pip install psutil

    Example:
        >>> if check_memory(threshold=85.0):
        ...     print("已执行内存清理")
        ⚠️ 内存使用率 87.5%, 执行垃圾回收
        已执行内存清理
    """
    try:
        import psutil
        import gc

        mem = psutil.virtual_memory()
        if mem.percent > threshold:
            from merit_extractor.utils import log
            log(f"⚠️ 内存使用率 {mem.percent:.1f}%, 执行垃圾回收")
            gc.collect()
            return True
    except ImportError:
        pass  # psutil未安装,跳过内存检查
    return False


# ========= 坐标系管理 (CRS Management) =========

def ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    确保GeoDataFrame使用WGS84坐标系(EPSG:4326)
    Ensure GeoDataFrame uses WGS84 coordinate system (EPSG:4326)

    功能说明:
    --------
    统一所有空间数据的坐标系为WGS84(经纬度),避免因坐标系不一致导致的
    空间运算错误。WGS84是最通用的地理坐标系,与GPS和大多数在线地图服务兼容。

    工作原理 (How It Works):
    -----------------------
    1. 检查CRS是否已定义:
       - 如果为None: 假定为WGS84并设置CRS(不改变坐标值)
    2. 检查当前CRS是否为WGS84:
       - 如果不是: 重投影到EPSG:4326(会改变坐标值)
    3. 如果已是WGS84: 直接返回,避免不必要的转换

    为什么需要坐标系统一 (Why Coordinate Unification is Needed):
    -------------------------------------------------------
    - 不同数据源可能使用不同坐标系
    - 空间运算要求所有数据使用相同坐标系
    - 距离计算、面积计算需要特定坐标系
    - WGS84作为基准,后续可根据需要投影到其他坐标系

    性能考虑 (Performance Considerations):
    ------------------------------------
    - 坐标转换是计算密集型操作
    - 对于大数据集可能耗时数秒到数分钟
    - 因此应预先检查,避免重复转换
    - 建议在数据加载后立即统一坐标系

    Args:
        gdf (gpd.GeoDataFrame): 输入的地理数据框
                               Input GeoDataFrame

    Returns:
        gpd.GeoDataFrame: 转换为WGS84坐标系的地理数据框
                         GeoDataFrame in WGS84 CRS

    常见坐标系 (Common CRS):
    ----------------------
    - EPSG:4326 (WGS84): 全球通用经纬度坐标系
    - EPSG:3857 (Web Mercator): 在线地图常用投影
    - EPSG:6933 (Equal Earth): 等面积投影,适合面积计算
    - EPSG:4490 (CGCS2000): 中国大地坐标系2000

    Example:
        >>> gdf = gpd.read_file("data.shp")  # 可能是任意CRS
        >>> gdf_wgs84 = ensure_wgs84(gdf)     # 确保为WGS84
        >>> print(gdf_wgs84.crs.to_epsg())
        4326
    """
    if gdf.crs is None:
        # CRS未定义,假定为WGS84
        return gdf.set_crs(4326)

    if gdf.crs.to_epsg() != 4326:
        # 需要重投影
        return gdf.to_crs(4326)

    # 已是WGS84
    return gdf


# ========= 数据验证 (Data Validation) =========

def valid_int(x: Any) -> bool:
    """
    检查值是否为有效的正整数
    Check if value is a valid positive integer

    功能说明:
    --------
    验证输入值是否为有效的正整数,用于检查河网ID、站点编码等关键字段。
    这是数据质量控制的重要环节,可提前发现并过滤无效数据。

    工作原理 (How It Works):
    -----------------------
    1. 尝试将输入转换为整数
    2. 检查转换后的值是否大于0
    3. 如果转换失败或值<=0,返回False

    为什么零和负数无效 (Why Zero and Negative Numbers are Invalid):
    ----------------------------------------------------------
    - 河网ID(COMID)通常从1开始编号
    - 0和负数表示缺失值或错误数据
    - 拓扑关系中,0或负数通常表示"无下游"或"无上游"

    Args:
        x (Any): 待检查的值(可以是int, float, str等)
                Value to check (can be int, float, str, etc.)

    Returns:
        bool: 如果是正整数返回True,否则返回False
             True if valid positive integer, False otherwise

    Example:
        >>> valid_int("123")
        True
        >>> valid_int(456)
        True
        >>> valid_int(0)
        False
        >>> valid_int(-1)
        False
        >>> valid_int("abc")
        False
        >>> valid_int(None)
        False
    """
    try:
        xi = int(x)
        return xi > 0
    except (TypeError, ValueError):
        return False
