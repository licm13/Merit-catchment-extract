# -*- coding: utf-8 -*-
"""
拓扑关系管理模块
Topology Relationship Management Module

本模块负责河网拓扑图构建、上游追溯算法等拓扑相关操作。
This module handles river network topology graph construction, upstream tracing algorithms, and other topology operations.
"""

from collections import defaultdict, deque
from typing import Dict, Set
import geopandas as gpd

from merit_extractor.utils import valid_int


# ========= 拓扑图构建 (Topology Graph Construction) =========

def build_upstream_graph(gdf_riv: gpd.GeoDataFrame) -> Dict[int, Set[int]]:
    """
    构建河网上游拓扑关系图
    Build upstream topology relationship graph for river network

    功能说明:
    --------
    该函数将河网的拓扑关系转换为高效的图数据结构,支持快速的上游追溯查询。
    拓扑图是流域提取的核心数据结构,决定了算法的性能和准确性。

    工作原理 (How It Works):
    -----------------------
    1. 检测可用的拓扑字段:
       - NextDownID: 下游河段引用(单向链接)
       - up1, up2, up3, up4: 上游河段引用(多向链接)
    2. 构建邻接表图结构:
       - 键: 下游河段COMID
       - 值: 该河段的所有上游河段COMID集合
    3. 验证拓扑数据可用性

    图数据结构设计 (Graph Structure Design):
    ---------------------------------------
    选择邻接表而非邻接矩阵的原因:
    - 河网是稀疏图(每个节点平均只有2-3个邻居)
    - 邻接表空间复杂度O(V+E),远小于邻接矩阵的O(V²)
    - 支持O(1)时间查询某节点的所有邻居
    - 动态添加节点和边更灵活

    图表示示例:
    ```
    G[100] = {101, 102}  # 河段100有两个上游: 101和102
    G[101] = {103, 104}  # 河段101有两个上游: 103和104
    G[102] = {105}       # 河段102有一个上游: 105
    ```

    拓扑字段说明 (Topology Field Description):
    ----------------------------------------
    **NextDownID** (下游河段ID):
    - 记录当前河段的下一个下游河段
    - 反向建图: 如果B是A的下游,则A是B的上游
    - 示例: 河段101的NextDownID=100 → G[100].add(101)

    **up1, up2, up3, up4** (上游河段ID):
    - 直接记录当前河段的上游河段(最多4个)
    - MERIT-Basins最多支持4条上游汇入
    - 示例: 河段100的up1=101, up2=102 → G[100]={101,102}

    为什么使用Set而非List (Why Set over List):
    ----------------------------------------
    - 自动去重(避免重复边)
    - O(1)成员测试(检查某河段是否为上游)
    - 无序性符合拓扑关系的语义

    数据质量检查 (Data Quality Checks):
    ----------------------------------
    建图后建议执行以下检查:
    ```python
    G = build_upstream_graph(gdf_riv)

    # 检查1: 统计孤立节点(无上游)
    isolated = sum(1 for v in G.values() if len(v) == 0)
    print(f"源头河段数: {isolated}")

    # 检查2: 统计汇流点(上游>1)
    confluences = sum(1 for v in G.values() if len(v) > 1)
    print(f"汇流点数: {confluences}")

    # 检查3: 最大上游数
    max_upstream = max(len(v) for v in G.values())
    print(f"最大上游数: {max_upstream}")

    # 检查4: 图规模
    print(f"图节点数: {len(G)}, 河网总数: {len(gdf_riv)}")
    ```

    Args:
        gdf_riv (gpd.GeoDataFrame): 河网数据,必须包含以下字段之一:
                                    River network data, must contain one of:
            - NextDownID: 下游河段ID (Downstream reach ID)
            - up1, up2, up3, up4: 上游河段ID (Upstream reach IDs)

    Returns:
        Dict[int, Set[int]]: 上游拓扑图 (Upstream topology graph)
            - 键: 下游河段COMID (Key: Downstream reach COMID)
            - 值: 该河段的所有上游河段COMID集合 (Value: Set of upstream reach COMIDs)

    Raises:
        RuntimeError: 如果河网数据缺少拓扑字段 (NextDownID 和 up1..up4 都不存在)
                     If river network lacks topology fields

    性能特征 (Performance Characteristics):
    -------------------------------------
    - 时间复杂度: O(n) 其中n为河段数量 (Time: O(n) where n = number of reaches)
    - 空间复杂度: O(n + m) 其中m为拓扑关系数 (Space: O(n + m) where m = number of topology links)
    - 典型构建时间: <1秒(对于10万河段) (Typical build time: <1s for 100k reaches)

    故障排除 (Troubleshooting):
    -------------------------
    问题: RuntimeError缺少拓扑字段
    解决: 1. 检查shapefile属性表是否包含NextDownID或up1-up4
         2. 确认使用的是MERIT-Basins河网数据(包含拓扑)
         3. 检查字段名大小写是否正确

    问题: 图规模异常小(少于预期)
    解决: 1. 检查COMID和NextDownID字段是否有大量无效值
         2. 验证valid_int函数的判断逻辑
         3. 查看原始数据是否有空值或格式问题

    问题: 内存占用过大
    解决: 1. 对于全球尺度数据,考虑分区域建图
         2. 使用更节省内存的数据类型(如int32而非int64)
         3. 仅保留研究区域相关的河段

    Example:
        >>> gdf_riv = gpd.read_file("river_network.shp")
        >>> G = build_upstream_graph(gdf_riv)
        >>> print(f"拓扑图规模: {len(G)} 个节点")
        拓扑图规模: 89754 个节点

        >>> # 查询某个河段的上游
        >>> outlet_comid = 12345
        >>> upstream_ids = G[outlet_comid]
        >>> print(f"河段 {outlet_comid} 有 {len(upstream_ids)} 个直接上游")
        河段 12345 有 2 个直接上游
    """
    # 检测可用的上游字段
    up_fields = [c for c in ["up1", "up2", "up3", "up4"] if c in gdf_riv.columns]
    has_next = "NextDownID" in gdf_riv.columns

    # 初始化图结构(默认字典,值为集合)
    G = defaultdict(set)

    # 方法1: 使用NextDownID构建反向关系
    if has_next:
        for _, r in gdf_riv[["COMID", "NextDownID"]].iterrows():
            c, nd = r["COMID"], r["NextDownID"]
            if valid_int(c) and valid_int(nd):
                # downstream -> upstream 的反向映射
                G[int(nd)].add(int(c))

    # 方法2: 使用up1-up4字段
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

    # 验证拓扑数据可用性
    if (not has_next) and (not up_fields):
        raise RuntimeError(
            "河网数据缺少拓扑字段 (NextDownID 或 up1..up4),无法构建上游关系图。\n"
            "请确认使用的是MERIT-Basins河网数据,且包含拓扑信息。"
        )

    return G


# ========= 上游追溯算法 (Upstream Tracing Algorithm) =========

def bfs_upstream(G: Dict[int, Set[int]], outlet: int) -> Set[int]:
    """
    使用广度优先搜索(BFS)追溯上游河网
    Trace upstream river network using Breadth-First Search (BFS)

    功能说明:
    --------
    该函数实现高效的上游河网追溯,从出口河段开始,逐层向上游扩展,直到到达
    所有源头。BFS算法保证了搜索的完整性和效率,是流域提取的核心算法。

    工作原理 (How It Works):
    -----------------------
    1. 初始化:
       - 创建已访问集合,包含出口节点
       - 创建队列,包含出口节点
    2. 循环(当队列非空):
       a. 从队列取出一个节点
       b. 从图中获取该节点的所有上游邻居
       c. 对每个未访问的邻居:
          - 标记为已访问
          - 加入队列待处理
    3. 返回完整的上游节点集合

    算法分析 (Algorithm Analysis):
    ----------------------------
    **时间复杂度**: O(V + E)
    - V: 上游网络的节点数(河段数)
    - E: 上游网络的边数(拓扑连接数)
    - 每个节点和边都恰好访问一次

    **空间复杂度**: O(V)
    - visited集合存储所有上游节点
    - 队列最坏情况下可能包含所有节点

    **为什么选择BFS而非DFS**:
    1. BFS按层级遍历,更符合河网结构的直觉
    2. BFS的队列实现比DFS的递归更节省内存
    3. BFS便于实现层级限制(如只追溯前N层)
    4. BFS避免了DFS可能的栈溢出问题

    算法可视化 (Algorithm Visualization):
    -----------------------------------
    ```
    初始状态:
    outlet = 100
    G = {100: {101, 102}, 101: {103}, 102: {104, 105}}

    迭代过程:
    Step 0: visited={100}, queue=[100]
    Step 1: 处理100, visited={100,101,102}, queue=[101,102]
    Step 2: 处理101, visited={100,101,102,103}, queue=[102,103]
    Step 3: 处理102, visited={100,101,102,103,104,105}, queue=[103,104,105]
    Step 4: 处理103, visited不变, queue=[104,105]
    Step 5: 处理104, visited不变, queue=[105]
    Step 6: 处理105, visited不变, queue=[]

    结果: visited={100,101,102,103,104,105}
    ```

    环路处理 (Cycle Handling):
    -------------------------
    理论上,河网是有向无环图(DAG),不应有环路。但实际数据可能因为:
    - 数据错误
    - 人工水利设施(如运河连接不同流域)
    - 数据处理错误

    而出现环路。visited集合机制自动防止无限循环:
    - 已访问节点不会再次加入队列
    - 即使有环路也能正常终止

    Args:
        G (Dict[int, Set[int]]): 上游拓扑图(由build_upstream_graph生成)
                                Upstream topology graph (from build_upstream_graph)
        outlet (int): 出口河段的COMID
                     COMID of the outlet reach

    Returns:
        Set[int]: 包含出口及其所有上游河段的COMID集合
                 Set of COMIDs including outlet and all upstream reaches

    性能优化建议 (Performance Optimization):
    -------------------------------------
    对于超大流域(>100万河段),可考虑:
    1. 添加深度限制(只追溯前N层)
    2. 使用优先队列实现启发式搜索
    3. 并行处理多个子流域
    4. 预计算并缓存常用流域的上游集合

    使用场景 (Use Cases):
    --------------------
    - 提取测站控制流域
    - 计算累积径流
    - 污染物传播模拟
    - 洪水演进分析
    - 流域边界自动划分

    Example:
        >>> # 基本用法
        >>> G = build_upstream_graph(gdf_riv)
        >>> outlet_comid = 12345
        >>> upstream = bfs_upstream(G, outlet_comid)
        >>> print(f"流域包含 {len(upstream)} 个河段")
        流域包含 8764 个河段

        >>> # 检查是否包含特定河段
        >>> if 67890 in upstream:
        ...     print("河段67890在该流域上游")

        >>> # 计算上游河段占比
        >>> total_reaches = len(gdf_riv)
        >>> coverage = len(upstream) / total_reaches * 100
        >>> print(f"该流域占全部河网的 {coverage:.2f}%")
        该流域占全部河网的 9.76%
    """
    # 初始化访问集合和队列
    visited = set([outlet])
    q = deque([outlet])

    # BFS主循环
    while q:
        cur = q.popleft()  # 取出队首节点

        # 获取当前节点的所有上游节点
        for u in G.get(cur, set()):
            if u not in visited:
                visited.add(u)  # 标记为已访问
                q.append(u)     # 加入队列待处理

    return visited
