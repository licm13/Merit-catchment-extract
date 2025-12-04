# -*- coding: utf-8 -*-
"""
Complex Test Cases for Hydrological Logic
复杂应用测试案例 - 水文逻辑一致性验证

This module tests the logical correctness of the merit_extractor package,
focusing on hydrological consistency rather than just basic functionality.

Test scenarios include:
- Nested basins: downstream basins must contain upstream basins
- Loop handling: BFS should terminate correctly even with cyclic data
- Area consistency: merged areas should match sum of component areas
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon

from merit_extractor.topology import build_upstream_graph, bfs_upstream
from merit_extractor.gis_utils import merge_catchments_fixed_robust, remove_small_holes


class TestTopologyBuilding(unittest.TestCase):
    """Test cases for upstream topology graph construction."""
    
    def test_simple_linear_topology(self):
        """Test building a simple linear river topology A -> B -> C."""
        # A(1) -> B(2) -> C(3) -> outlet(0)
        riv_data = {
            'COMID': [1, 2, 3],
            'NextDownID': [2, 3, 0]  # 0 means outlet/ocean
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        # Check upstream relationships
        self.assertIn(1, G.get(2, set()), "River 1 should be upstream of 2")
        self.assertIn(2, G.get(3, set()), "River 2 should be upstream of 3")
        self.assertNotIn(3, G.get(0, set()), "Outlet 0 should have no upstream in G")
    
    def test_confluence_topology(self):
        """Test a confluence where two tributaries join."""
        # Confluence pattern:
        #   101 \
        #        -> 103 -> 105 -> 0
        #   102 /
        #   104 /
        riv_data = {
            'COMID': [101, 102, 103, 104, 105],
            'NextDownID': [103, 103, 105, 105, 0]
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        # Check that 103 has two upstream reaches (101, 102)
        upstream_103 = G.get(103, set())
        self.assertEqual(len(upstream_103), 2, "103 should have 2 upstream reaches")
        self.assertIn(101, upstream_103)
        self.assertIn(102, upstream_103)
        
        # Check that 105 has two upstream reaches (103, 104)
        upstream_105 = G.get(105, set())
        self.assertEqual(len(upstream_105), 2, "105 should have 2 upstream reaches")
        self.assertIn(103, upstream_105)
        self.assertIn(104, upstream_105)


class TestBFSUpstream(unittest.TestCase):
    """Test cases for BFS upstream tracing algorithm."""
    
    def test_bfs_linear_network(self):
        """Test BFS on a simple linear network."""
        # 1 -> 2 -> 3
        G = {
            3: {2},
            2: {1},
            1: set()
        }
        
        # From outlet 3, should find all upstream
        upstream = bfs_upstream(G, 3)
        self.assertEqual(upstream, {1, 2, 3}, "BFS should find all upstream reaches")
        
        # From middle point 2
        upstream_2 = bfs_upstream(G, 2)
        self.assertEqual(upstream_2, {1, 2}, "BFS from 2 should only find 1 and 2")
        
        # From headwater 1
        upstream_1 = bfs_upstream(G, 1)
        self.assertEqual(upstream_1, {1}, "BFS from headwater should only find itself")
    
    def test_bfs_confluence(self):
        """Test BFS handles confluences correctly."""
        # Confluence: 1, 2 -> 3 -> 4
        G = {
            4: {3},
            3: {1, 2},
            1: set(),
            2: set()
        }
        
        upstream = bfs_upstream(G, 4)
        self.assertEqual(upstream, {1, 2, 3, 4}, "Should find all upstream including both tributaries")


class TestHydrologicalLogic(unittest.TestCase):
    """
    Test hydrological logic consistency.
    
    Key principles:
    - Downstream station's catchment area must be >= upstream station's
    - Upstream catchment must be spatially contained within downstream catchment
    """
    
    def test_nested_basins_area(self):
        """
        Test nested basin logic: downstream basin area must be >= upstream.
        
        Topology: A(upstream) -> B(middle) -> C(downstream)
        """
        # Build topology
        riv_data = {
            'COMID': [1, 2, 3],
            'NextDownID': [2, 3, 0]
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        # Create unit catchment geometries (simple adjacent rectangles)
        # Catchment 1: (0,0) to (1,1)
        # Catchment 2: (1,0) to (2,1)
        # Catchment 3: (2,0) to (3,1)
        cat_geoms = {
            1: Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            2: Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            3: Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])
        }
        
        # Get upstream sets
        upstream_1 = bfs_upstream(G, 1)  # Should be {1}
        upstream_2 = bfs_upstream(G, 2)  # Should be {1, 2}
        upstream_3 = bfs_upstream(G, 3)  # Should be {1, 2, 3}
        
        self.assertEqual(upstream_1, {1})
        self.assertEqual(upstream_2, {1, 2})
        self.assertEqual(upstream_3, {1, 2, 3})
        
        # Merge catchments for each outlet
        geom_1 = merge_catchments_fixed_robust([cat_geoms[i] for i in upstream_1])
        geom_2 = merge_catchments_fixed_robust([cat_geoms[i] for i in upstream_2])
        geom_3 = merge_catchments_fixed_robust([cat_geoms[i] for i in upstream_3])
        
        # Area check: downstream >= upstream
        self.assertGreater(
            geom_2.area, geom_1.area,
            "Middle basin area should be greater than upstream basin"
        )
        self.assertGreater(
            geom_3.area, geom_2.area,
            "Downstream basin area should be greater than middle basin"
        )
        self.assertGreater(
            geom_3.area, geom_1.area,
            "Downstream basin area should be greater than upstream basin"
        )
    
    def test_nested_basins_spatial_containment(self):
        """
        Test that upstream basin is spatially contained within downstream basin.
        
        Due to buffer operations, we use a small tolerance for the containment check.
        """
        # Build topology: 1 -> 2
        riv_data = {
            'COMID': [1, 2],
            'NextDownID': [2, 0]
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        # Create adjacent unit catchments
        cat_geoms = {
            1: Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            2: Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
        }
        
        # Get upstream sets
        upstream_1 = bfs_upstream(G, 1)  # {1}
        upstream_2 = bfs_upstream(G, 2)  # {1, 2}
        
        # Merge catchments
        geom_1 = merge_catchments_fixed_robust([cat_geoms[i] for i in upstream_1])
        geom_2 = merge_catchments_fixed_robust([cat_geoms[i] for i in upstream_2])
        
        # Spatial containment check
        # The upstream catchment should be contained within downstream
        # Due to floating point and buffer operations, we check that the difference is negligible
        diff = geom_1.difference(geom_2)
        self.assertLess(
            diff.area, 1e-6,
            "Upstream catchment should be contained within downstream catchment"
        )


class TestLoopHandling(unittest.TestCase):
    """
    Test that algorithms handle loops/cycles gracefully.
    
    While river networks should be DAGs (directed acyclic graphs),
    data errors might create cycles. The BFS should not enter infinite loops.
    """
    
    def test_simple_cycle(self):
        """Test BFS handles a simple 2-node cycle without infinite loop."""
        # Create a cycle: 1 <-> 2 (each claims the other as upstream)
        riv_data = {
            'COMID': [1, 2],
            'NextDownID': [2, 1]  # This creates a cycle
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        # BFS should terminate and return both nodes
        try:
            ids = bfs_upstream(G, 1)
            self.assertEqual(len(ids), 2, "Should find both nodes in cycle")
            self.assertIn(1, ids)
            self.assertIn(2, ids)
        except RecursionError:
            self.fail("BFS entered infinite loop - cycle not handled correctly")
    
    def test_larger_cycle(self):
        """Test BFS handles a larger cycle (3+ nodes)."""
        # Create a 3-node cycle: 1 -> 2 -> 3 -> 1
        riv_data = {
            'COMID': [1, 2, 3],
            'NextDownID': [2, 3, 1]  # Cycle
        }
        gdf_riv = gpd.GeoDataFrame(riv_data)
        G = build_upstream_graph(gdf_riv)
        
        try:
            ids = bfs_upstream(G, 1)
            self.assertEqual(len(ids), 3, "Should find all nodes in cycle")
        except RecursionError:
            self.fail("BFS entered infinite loop on larger cycle")


class TestGeometryMerging(unittest.TestCase):
    """Test geometry merging and topology fixing functions."""
    
    def test_merge_adjacent_polygons(self):
        """Test merging two adjacent polygons into one."""
        # Two perfectly adjacent squares
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
        
        merged = merge_catchments_fixed_robust([p1, p2])
        
        # Should be a single polygon
        self.assertIsInstance(merged, (Polygon, MultiPolygon))
        
        # Area should be approximately 2 (two unit squares)
        self.assertAlmostEqual(merged.area, 2.0, places=3)
    
    def test_merge_with_small_gap(self):
        """Test that small gaps between polygons are filled."""
        # Two squares with a tiny gap (simulating raster-to-vector artifacts)
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(1.001, 0), (2.001, 0), (2.001, 1), (1.001, 1)])  # 0.001 gap
        
        merged = merge_catchments_fixed_robust([p1, p2])
        
        # After gap filling, should be approximately 2 unit squares
        # (allowing for some variation due to buffer operations)
        self.assertGreater(merged.area, 1.9)
        self.assertLess(merged.area, 2.1)
    
    def test_preserve_large_holes(self):
        """Test that large holes (representing lakes) are preserved."""
        # Outer square with a large inner hole (lake)
        outer = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        # Inner hole representing a 2x2 lake (4 km² if coordinates are in degrees scaled)
        hole = Polygon([(4, 4), (6, 4), (6, 6), (4, 6)])
        polygon_with_lake = Polygon(outer.exterior.coords, [hole.exterior.coords])
        
        # Remove small holes should keep this large hole
        # Note: The remove_small_holes function works in degrees, and 1 degree² ≈ 10000 km²
        # So a 4 unit² hole in "degree coordinates" would be 4 * 10000 = 40000 km²
        # We need to set min_hole_km2 appropriately
        result = remove_small_holes(polygon_with_lake, min_area_km2=30000)
        
        # Should still have the interior hole
        if isinstance(result, Polygon):
            self.assertEqual(len(result.interiors), 1, "Large lake hole should be preserved")
    
    def test_remove_small_holes(self):
        """Test that small holes (artifacts) are removed."""
        # Outer square with a tiny inner hole (artifact)
        outer = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        # Tiny hole (0.001 x 0.001 = 0.000001 units², which is very small)
        # In degree coordinates, this is about 0.01 km² (much less than 1 km² threshold)
        tiny_hole = Polygon([(4.9995, 4.9995), (5.0005, 4.9995), (5.0005, 5.0005), (4.9995, 5.0005)])
        polygon_with_artifact = Polygon(outer.exterior.coords, [tiny_hole.exterior.coords])
        
        # Remove holes smaller than 1 km² 
        # The tiny hole is ~0.01 km² which should be removed
        result = remove_small_holes(polygon_with_artifact, min_area_km2=1.0)
        
        # Tiny hole should be removed
        if isinstance(result, Polygon):
            self.assertEqual(len(result.interiors), 0, "Tiny artifact hole should be removed")


class TestAreaConsistency(unittest.TestCase):
    """Test that area calculations are consistent."""
    
    def test_merged_area_approximately_equals_sum(self):
        """Test that merged polygon area approximately equals sum of parts."""
        # Create three adjacent unit squares
        p1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        p2 = Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])
        p3 = Polygon([(2, 0), (3, 0), (3, 1), (2, 1)])
        
        original_sum = p1.area + p2.area + p3.area
        
        merged = merge_catchments_fixed_robust([p1, p2, p3])
        
        # Area difference should be less than 1%
        diff_pct = abs(merged.area - original_sum) / original_sum * 100
        self.assertLess(diff_pct, 1.0, "Merged area should be within 1% of sum")


if __name__ == '__main__':
    unittest.main(verbosity=2)
