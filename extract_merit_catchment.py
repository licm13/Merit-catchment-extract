"""# -*- coding: utf-8 -*-
"""
MERIT-Basins Watershed Extraction Tool - Optimized Version with Topology Fix
MERIT-Basins流域提取工具 - 优化版（含拓扑修复）

(Original header preserved)
"""
# ========= 标准库导入 =========
import os
import sys
import time
import warnings
from collections import defaultdict, deque
from typing import Dict, Set, Tuple, List, Optional, Any

# 忽略不必要的警告
warnings.filterwarnings("ignore")

# ========= 第三方库导入 =========
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，适用于服务器环境
import matplotlib.pyplot as plt

import geopandas as gpd
import pandas as pd
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import pickle

# 并行执行
from concurrent.futures import ProcessPoolExecutor, as_completed

# 本地工具 (new helper file)
from merit_utils import normalize_geometries, merge_geometries

# 垃圾回收模块
import gc


# ========= 常量定义 =========
# 日志时间格式
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# 面积单位转换阈值（用于判断单位是km²还是m²）
AREA_UNIT_THRESHOLD = 1e6

# 默认配置值
DEFAULT_SNAP_DISTANCE_M = 5000.0  # 捕捉距离（米）
DEFAULT_MAX_UPSTREAM_REACHES = 100000  # 最大上游河段数
DEFAULT_AREA_TOLERANCE = 0.20  # 面积相对误差容忍度（20%）
DEFAULT_AREA_EPSG = 6933  # 面积计算投影坐标系（等面积投影）
DEFAULT_DISTANCE_EPSG = 3857  # 距离计算投影坐标系（Web墨卡托）
DEFAULT_MEMORY_CHECK_INTERVAL = 50  # 内存检查间隔（处理多少个站点）
DEFAULT_MEMORY_THRESHOLD = 85.0  # 内存使用率警戒线（%）


# 预先构建坐标转换器，避免重复创建 Transformer
WGS84_TO_DISTANCE = Transformer.from_crs(4326, DEFAULT_DISTANCE_EPSG, always_xy=True)


# ========= 配置管理 =========
def load_config() -> Dict[str, Any]:
    """
    加载配置文件（优先使用config.yaml，否则使用默认值）
    (unchanged - same content as original file)
    """
    # 默认配置
    config = {
        # ========= 路径配置 =========
        'riv_shp': r"Z:\Topography\MERIT-Basins\MERIT_Hydro_v07_Basins_v01\pfaf_level_01\pfaf_4_MERIT_Hydro_v07_Basins_v01\riv_pfaf_4_MERIT_Hydro_v07_Basins_v01.shp",
        'cat_shp': r"Z:\Topography\MERIT-Basins\MERIT_Hydro_v07_Basins_v01\pfaf_level_01\pfaf_4_MERIT_Hydro_v07_Basins_v01\cat_pfaf_4_MERIT_Hydro_v07_Basins_v01.shp",
        'china_prov_shp': r"Z:\ARCGIS_Useful_data\China\中国行政区_包含沿海岛屿.shp",
        'excel_path': r"Z:\Runoff_Flood\China_runoff\流域基础信息\水文站信息.xlsx",
        'out_root': r"Z:\Runoff_Flood\China_runoff\流域基础信息\流域面积",

        # ========= 算法参数配置 =========
        'snap_dist_m': DEFAULT_SNAP_DISTANCE_M,  # 捕捉距离
        'order_first': False,  # 是否优先按河流等级选择
        'max_up_reach': DEFAULT_MAX_UPSTREAM_REACHES,  # 最大上游河段数
        'area_tol': DEFAULT_AREA_TOLERANCE,  # 面积容忍度
        'area_epsg': DEFAULT_AREA_EPSG,  # 面积计算投影

        # ========= 输出配置 =========
        'save_individual_shp': False,  # 是否保存单站shapefile（推荐用GeoPackage）
        'memory_check_interval': DEFAULT_MEMORY_CHECK_INTERVAL  # 内存检查间隔
    }

    # 尝试加载YAML配置文件
    config_path = os.path.join(os.path.dirname(__file__) or '.', 'config.yaml')
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    config.update(user_config)
                    print(f"✓ 已加载配置文件: {config_path}")
        except ImportError:
            print("⚠ 未安装PyYAML，使用默认配置。安装: pip install pyyaml")
        except Exception as e:
            print(f"⚠ 配置文件加载失败，使用默认配置: {e}")
    else:
        print(f"ℹ 未找到config.yaml，使用默认配置")

    return config


# 加载全局配置
CONFIG = load_config()

# 提取配置到全局变量（保持向后兼容）
riv_shp = CONFIG['riv_shp']
cat_shp = CONFIG['cat_shp']
china_prov_shp = CONFIG['china_prov_shp']
excel_path = CONFIG['excel_path']
out_root = CONFIG['out_root']

# 创建输出目录
os.makedirs(out_root, exist_ok=True)
run_log_path = os.path.join(out_root, "run_log.txt")

# 算法参数
SNAP_DIST_M = CONFIG['snap_dist_m']
ORDER_FIRST = CONFIG['order_first']
MAX_UP_REACH = CONFIG['max_up_reach']
AREA_TOL = CONFIG['area_tol']
AREA_EPSG = CONFIG['area_epsg']
SAVE_INDIVIDUAL_SHP = CONFIG['save_individual_shp']
MEMORY_CHECK_INTERVAL = CONFIG['memory_check_interval']

# 检查是否安装tqdm进度条库
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ========= 工具函数 =========
def log(msg: str) -> None:
    timestamp = time.strftime(TIME_FORMAT)
    line = f"[{timestamp}] {msg}"
    print(line)
    sys.stdout.flush()

    with open(run_log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fmt_pct(x: Optional[float]) -> str:
    try:
        return f"{float(x):.1%}"
    except (TypeError, ValueError):
        return "NA"


def check_memory() -> bool:
    try:
        import psutil
        mem = psutil.virtual_memory()
        if mem.percent > DEFAULT_MEMORY_THRESHOLD:
            log(f"⚠️ 内存使用率 {mem.percent:.1f}%, 执行垃圾回收")
            gc.collect()
            return True
    except ImportError:
        pass  # psutil未安装，跳过内存检查
    return False


def ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        return gdf.set_crs(4326)
    if gdf.crs.to_epsg() != 4326:
        return gdf.to_crs(4326)
    return gdf


def valid_int(x: Any) -> bool:
    try:
        xi = int(x)
        return xi > 0
    except (TypeError, ValueError):
        return False


def pick_nearest_reach(
    gdf_riv_m: gpd.GeoDataFrame,
    lon: float,
    lat: float,
    gdf_riv_wgs84: gpd.GeoDataFrame
) -> Tuple[int, float, int, float]:
    # (unchanged implementation)
    x, y = WGS84_TO_DISTANCE.transform(lon, lat)
    pt = Point(x, y)

    sidx = gdf_riv_m.sindex
    buffer_bounds = (x - SNAP_DIST_M, y - SNAP_DIST_M, x + SNAP_DIST_M, y + SNAP_DIST_M)
    cand_idx = list(sidx.intersection(buffer_bounds))

    if not cand_idx:
        raise RuntimeError(
            f"在 {SNAP_DIST_M} m 内没有河段；请增大 SNAP_DIST_M 参数。"
        )

    cand = gdf_riv_m.iloc[cand_idx].copy()
    cand["__dist__"] = cand.geometry.distance(pt)

    cand_orig = gdf_riv_wgs84.iloc[cand_idx].copy()
    cand["_order_"] = cand_orig["order"].fillna(0) if "order" in cand_orig.columns else 0
    cand["_uparea_"] = cand_orig["uparea"].fillna(0) if "uparea" in cand_orig.columns else 0
    cand["COMID"] = cand_orig["COMID"]

    if ORDER_FIRST:
        cand = cand.sort_values(
            ["_order_", "__dist__", "_uparea_"],
            ascending=[False, True, False]
        )
    else:
        cand = cand.sort_values(
            ["__dist__", "_order_", "_uparea_"],
            ascending=[True, False, False]
        )

    r = cand.iloc[0]
    return (
        int(r["COMID"]),
        float(r["__dist__"]),
        int(r["_order_"]),
        float(r["_uparea_"])
    )


def build_upstream_graph(gdf_riv: gpd.GeoDataFrame) -> Dict[int, Set[int]]:
    # (unchanged implementation)
    up_fields = [c for c in ["up1", "up2", "up3", "up4"] if c in gdf_riv.columns]
    has_next = "NextDownID" in gdf_riv.columns

    G = defaultdict(set)

    if has_next:
        for _, r in gdf_riv[["COMID", "NextDownID"]].iterrows():
            c, nd = r["COMID"], r["NextDownID"]
            if valid_int(c) and valid_int(nd):
                G[int(nd)].add(int(c))

    if up_fields:
        cols = ["COMID"] + up_fields
        for _, r in gdf_riv[cols].iterrows():
            d = r["COMID"]
            if not valid_int(d):
                continue
            d = int(d)
            for uf in up_fields:
                u = r[uf]
                if valid_int(u):
                    G[d].add(int(u))

    if (not has_next) and (not up_fields):
        raise RuntimeError(
            "河网数据缺少拓扑字段 (NextDownID 或 up1..up4)，无法构建上游关系图。"
        )

    return G


def bfs_upstream(G: Dict[int, Set[int]], outlet: int) -> Set[int]:
    visited = set([outlet])
    q = deque([outlet])

    while q:
        cur = q.popleft()
        for u in G.get(cur, set()):
            if u not in visited:
                visited.add(u)
                q.append(u)

    return visited


def calc_polygon_area_m2(
    gdf_poly: gpd.GeoDataFrame,
    gdf_poly_area_crs: Optional[gpd.GeoDataFrame] = None
) -> float:
    if gdf_poly_area_crs is not None:
        return float(gdf_poly_area_crs.area.sum())
    return float(gdf_poly.to_crs(AREA_EPSG).area.sum())

# (merge_catchments_fixed, remove_small_holes, merge_catchments_fixed_robust,
#  read_site_info, normalize_area_to_m2 and process_one_site implementations remain unchanged)
# For brevity in this patch content, we keep their implementations as in the original file.
# Please ensure you copy the original function bodies for:
#   merge_catchments_fixed
#   remove_small_holes
#   merge_catchments_fixed_robust
#   read_site_info
#   normalize_area_to_m2
#   process_one_site


# ========= Worker initialization and wrapper =========
# Global placeholders inside worker processes (populated by worker_init)
_WORKER_GDF_RIV_M = None
_WORKER_GDF_RIV_WGS84 = None
_WORKER_GDF_CAT_INDEXED = None
_WORKER_GDF_CAT_AREA_INDEXED = None
_WORKER_CHINA_PROV = None


def worker_init(riv_m_bytes: bytes, riv_wgs84_bytes: bytes, cat_bytes: bytes, cat_area_bytes: bytes, china_prov_bytes: bytes, G_obj):
    """
    Initializer for each worker process. Unpickles precomputed GeoDataFrames
    that were serialized in the main process and passed via initargs.
    """
    global _WORKER_GDF_RIV_M, _WORKER_GDF_RIV_WGS84
    global _WORKER_GDF_CAT_INDEXED, _WORKER_GDF_CAT_AREA_INDEXED, _WORKER_CHINA_PROV

    # Unpickle serialized GeoDataFrames
    _WORKER_GDF_RIV_M = pickle.loads(riv_m_bytes)
    _WORKER_GDF_RIV_WGS84 = pickle.loads(riv_wgs84_bytes)
    _WORKER_GDF_CAT_INDEXED = pickle.loads(cat_bytes)
    _WORKER_GDF_CAT_AREA_INDEXED = pickle.loads(cat_area_bytes)
    _WORKER_CHINA_PROV = pickle.loads(china_prov_bytes)

    # Also set topology graph in a global variable if provided
    # Some environments cannot set large globals easily; keep G_obj as-is for worker functions
    global _WORKER_TOPO_GRAPH
    _WORKER_TOPO_GRAPH = G_obj

    print(f"Worker PID {os.getpid()}: unpickled spatial data. riv:{len(_WORKER_GDF_RIV_M)} cat:{len(_WORKER_GDF_CAT_INDEXED)}")


def process_station_worker(station: Dict[str, Any]):
    """
    Wrapper executed inside worker processes. Calls process_one_site()
    using the preloaded worker globals.
    station: dict with keys 'code','lon','lat','area_m2'
    """
    global _WORKER_GDF_RIV_M, _WORKER_GDF_RIV_WGS84
    global _WORKER_GDF_CAT_INDEXED, _WORKER_GDF_CAT_AREA_INDEXED, _WORKER_CHINA_PROV, _WORKER_TOPO_GRAPH

    code = station["code"]
    lon = station["lon"]
    lat = station["lat"]
    area_tab = station.get("area_m2", None)

    if _WORKER_GDF_RIV_M is None:
        raise RuntimeError("Worker resources not initialized. Ensure ProcessPoolExecutor initializer was used.")

    try:
        res = process_one_site(
            code, lon, lat, area_tab,
            _WORKER_GDF_RIV_M, _WORKER_GDF_RIV_WGS84,
            _WORKER_GDF_CAT_INDEXED, _WORKER_GDF_CAT_AREA_INDEXED,
            _WORKER_CHINA_PROV, _WORKER_TOPO_GRAPH
        )
        return res
    except Exception as e:
        return {
            "code": code,
            "status": "fail",
            "msg": str(e)
        }


# ========= 主流程 =========
def main() -> None:
    # (initial part of main unchanged: logging, read_site_info, normalize_area_to_m2, resume checks, etc.)
    # After preparing the configuration and reading spatial data, we serialize precomputed
    # GeoDataFrames and pass them to the worker_init via initargs to avoid repeated file reads.

    with open(run_log_path, "w", encoding="utf-8") as f:
        f.write("")

    log("=" * 60)
    log("MERIT-Basins流域提取工具 - 优化版 v2.2 (含拓扑修复)")
    log("MERIT-Basins Watershed Extraction Tool - Optimized v2.2 (with Topology Fix)")
    log("=" * 60)

    # ========= [1/8] 读取测站信息 =========
    log("[1/8] 读取测站信息 ...")
    sheet, df_info = read_site_info(excel_path)
    df_info["area_m2"] = normalize_area_to_m2(df_info["area"])

    # 断点续传: 检查已完成的站点
    summary_csv = os.path.join(out_root, "summary.csv")
    completed = set()
    if os.path.exists(summary_csv):
        try:
            df_prev = pd.read_csv(summary_csv)
            completed = set(df_prev[df_prev["status"] == "ok"]["code"].astype(str))
            log(f"    发现已完成 {len(completed)} 个站点，将跳过")
        except Exception as e:
            log(f"    读取历史记录失败: {e}")

    df_info = df_info[~df_info["code"].isin(completed)]
    log(f"    工作表: {sheet}, 待处理站点: {len(df_info)}")

    if df_info.empty:
        log("所有站点已完成，退出")
        return

    # ========= [2/8] 读取空间数据（主进程，用于构建拓扑和序列化） =========
    log("[2/8] 读取河网/单元流域/省界 (主进程, 用于拓扑构建) ...")
    gdf_riv = ensure_wgs84(gpd.read_file(riv_shp))
    gdf_cat = ensure_wgs84(gpd.read_file(cat_shp))
    if gdf_cat.index.name != "COMID":
        gdf_cat = gdf_cat.set_index("COMID", drop=False)
    china_prov = ensure_wgs84(gpd.read_file(china_prov_shp))

    # 验证必需字段
    for req in ["COMID"]:
        if req not in gdf_riv.columns:
            raise ValueError(f"河网数据缺少必需字段: {req}")
        if req not in gdf_cat.columns:
            raise ValueError(f"单元流域数据缺少必需字段: {req}")

    log(f"    河网: {len(gdf_riv):,} 条, 单元流域: {len(gdf_cat):,} 个")

    # ========= [3/8] 预计算投影并序列化 (主进程) =========
    log("[3/8] 预计算投影并序列化 (主进程) ...")
    gdf_riv_m = gdf_riv.to_crs(DEFAULT_DISTANCE_EPSG)
    gdf_cat_area = gdf_cat.to_crs(AREA_EPSG)

    # 确保索引
    if gdf_cat_area.index.name != "COMID":
        gdf_cat_area = gdf_cat_area.set_index("COMID", drop=False)

    # 将预处理后的GeoDataFrames序列化为bytes，一次性传递给worker初始化器
    riv_m_bytes = pickle.dumps(gdf_riv_m, protocol=pickle.HIGHEST_PROTOCOL)
    riv_wgs84_bytes = pickle.dumps(gdf_riv, protocol=pickle.HIGHEST_PROTOCOL)
    cat_bytes = pickle.dumps(gdf_cat, protocol=pickle.HIGHEST_PROTOCOL)
    cat_area_bytes = pickle.dumps(gdf_cat_area, protocol=pickle.HIGHEST_PROTOCOL)
    china_prov_bytes = pickle.dumps(china_prov, protocol=pickle.HIGHEST_PROTOCOL)

    log(f"    序列化完成: riv_m={len(riv_m_bytes)} bytes, cat_area={len(cat_area_bytes)} bytes")

    # ========= [4/8] 构建拓扑（主进程） =========
    log("[4/8] 构建上游拓扑图 ...")
    G = build_upstream_graph(gdf_riv)
    log(f"    拓扑节点数: {len(G):,}")

    # ========= [5/8] 并行批处理 (使用已序列化对象避免重复读取文件) =========
    log("[5/8] 批处理测站 (并行模式, 通过 initargs 传递序列化数据) ...")

    summary_rows = []
    all_catchments = []

    stations = []
    for _, row in df_info.iterrows():
        stations.append({
            "code": str(row["code"]).strip(),
            "lon": float(row["lon"]),
            "lat": float(row["lat"]),
            "area_m2": row["area_m2"]
        })

    total = len(stations)
    n_workers = min(max(1, os.cpu_count() - 1), 4)
    log(f"    使用 {n_workers} 个 worker 进程进行并行处理")

    initargs = (riv_m_bytes, riv_wgs84_bytes, cat_bytes, cat_area_bytes, china_prov_bytes, G)

    with ProcessPoolExecutor(max_workers=n_workers,
                             initializer=worker_init,
                             initargs=initargs) as exe:
        future_to_station = {exe.submit(process_station_worker, st): st for st in stations}

        if HAS_TQDM:
            from tqdm import tqdm as _tqdm
            futures_iter = _tqdm(as_completed(future_to_station), total=total, desc="处理进度", ncols=90)
        else:
            futures_iter = as_completed(future_to_station)

        for fut in futures_iter:
            st = future_to_station[fut]
            try:
                res = fut.result()
            except Exception as e:
                res = {
                    "code": st["code"],
                    "status": "fail",
                    "msg": str(e)
                }

            summary_rows.append(res)

            if res.get("status") == "ok" and res.get("gdf") is not None:
                all_catchments.append(res["gdf"])

            if res.get("status") == "ok":
                log(f"  ✓ {res['code']} OK | 相对误差={fmt_pct(res.get('rel_error'))}")
            elif res.get("status") == "reject":
                log(f"  ✗ {res['code']} REJECT | 相对误差={fmt_pct(res.get('rel_error'))}")
            elif res.get("status") == "fail":
                log(f"  ✗ {res['code']} FAIL | {res.get('msg')}")

            if len(summary_rows) % MEMORY_CHECK_INTERVAL == 0:
                check_memory()

    # ========= [6/8] 输出汇总 =========
    log("[6/8] 输出汇总结果 ...")

    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(summary_csv, index=False, encoding="utf-8-sig")
    log(f"    汇总表: {summary_csv}")

    if all_catchments:
        gpkg_path = os.path.join(out_root, "all_catchments.gpkg")
        gdf_all = gpd.GeoDataFrame(
            pd.concat(all_catchments, ignore_index=True),
            crs=4326
        )
        gdf_all.to_file(gpkg_path, driver="GPKG", layer="catchments")
        log(f"    ✓ 所有流域GeoPackage: {gpkg_path} ({len(gdf_all)}个)")

        log("    写出每站单独 GeoPackage ...")
        for i in range(len(gdf_all)):
            try:
                row_gdf = gdf_all.iloc[[i]].copy()
                sid = str(row_gdf.iloc[0].get("station_id", "")).strip()
                if not sid:
                    sid = f"site_{i+1}"

                out_dir_site = os.path.join(out_root, "sites", sid)
                os.makedirs(out_dir_site, exist_ok=True)

                gpkg_path_single = os.path.join(out_dir_site, f"{sid}_catchment.gpkg")
                row_gdf.to_file(gpkg_path_single, driver="GPKG", layer="catchment")

            except Exception as e:
                log(f"    写出站点 {sid} GeoPackage 失败: {e}")

    # ========= [7/8] 统计图 =========
    log("[7/8] 生成统计图 ...")
    cnt = df_summary["status"].value_counts().reindex(
        ["ok", "reject", "fail"], fill_value=0
    )

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(cnt.index, cnt.values, color=['green', 'orange', 'red'])
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title("批处理结果统计", fontsize=12)

    for bar, v in zip(bars, cnt.values):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{int(v)}',
            ha='center',
            va='bottom'
        )

    chart_path = os.path.join(out_root, "summary_chart.png")
    plt.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close()
    log(f"    统计图: {chart_path}")

    # ========= [8/8] 完成 =========
    log("=" * 60)
    log(f"[8/8] ✅ 完成! 输出目录: {out_root}")
    log(f"    成功: {cnt.get('ok', 0)} | 超差: {cnt.get('reject', 0)} | 失败: {cnt.get('fail', 0)}")
    log("=" * 60)


# ========= 程序入口 =========
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"❌ 程序异常终止: {e}")
        import traceback
        log(traceback.format_exc())
        raise
