"""
DXF Importer for Thermal Bridge Simulation
Extracts 2D geometry from DXF files for use in thermal simulation scenarios.
"""

import ezdxf
from typing import Dict, List, Any, Tuple, Optional
import logging
import math
import tempfile
import os
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union, polygonize, linemerge

class DXFImporter:
    def __init__(self, dxf_stream):
        """
        Initialize with a file-like object (bytes) of the DXF.
        """
        try:
            # Create a temporary file to handle the stream
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(dxf_stream.read())
                tmp_path = tmp.name

            try:
                self.doc = ezdxf.readfile(tmp_path)
                self.msp = self.doc.modelspace()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            
        except Exception as e:
            logging.error(f"Failed to load DXF: {e}")
            raise ValueError(f"Invalid DXF file: {e}")

    def get_layers(self) -> List[str]:
        """Return a sorted list of layer names found in the ModelSpace."""
        layers = set()
        for entity in self.msp:
            layers.add(entity.dxf.layer)
        return sorted(list(layers))

    def get_preview_data(self, layer_mapping: Dict[str, str], 
                         simplify_tolerance: float = 1.0,
                         min_area_threshold: float = 5.0) -> Dict[str, Any]:
        """
        Get preview data for visualization without full scenario conversion.
        
        Returns:
            Dict with 'polygons' (list of {material, coords, area}), 'stats', and 'bounds'
        """
        # Reuse extract logic but return intermediate data
        scenario = self.extract_scenario(layer_mapping, simplify_tolerance, min_area_threshold)
        
        # Build preview polygons from scenario
        preview_polys = []
        points = scenario.get('points', {})
        for el in scenario.get('elements', []):
            if el.get('type') == 'polygon':
                coords = [points[p] for p in el.get('points', [])]
                if len(coords) >= 3:
                    from shapely.geometry import Polygon as ShapelyPolygon
                    poly = ShapelyPolygon(coords)
                    preview_polys.append({
                        'material': el.get('material', 'unknown'),
                        'name': el.get('name', ''),
                        'coords': coords,
                        'area': poly.area
                    })
        
        # Calculate stats
        bounds = scenario.get('canvas', {}).get('bounds', [0, 500, 0, 500])
        total_area = sum(p['area'] for p in preview_polys)
        materials_used = set(p['material'] for p in preview_polys)
        
        return {
            'polygons': preview_polys,
            'stats': {
                'polygon_count': len(preview_polys),
                'total_area_mm2': total_area,
                'materials_used': list(materials_used),
                'point_count': len(points)
            },
            'bounds': bounds
        }


    def extract_scenario(self, layer_mapping: Dict[str, str], 
                         simplify_tolerance: float = 1.0,
                         min_area_threshold: float = 5.0) -> Dict[str, Any]:
        """
        Convert mapped layers into a Scenario dictionary.
        
        Args:
            layer_mapping: Dict mapping DXF Layer Name -> Material ID (string)
            simplify_tolerance: Douglas-Peucker simplification tolerance in mm (default: 1.0)
            min_area_threshold: Minimum polygon area in mm² to include (default: 5.0)
            
        Returns:
            Dict matching the Scenario schema.
        """
        
        # 1. Collect raw geometries per material
        raw_polys_by_mat = {mat_id: [] for mat_id in set(layer_mapping.values()) if mat_id}
        
        # We also collect all lines/arcs for "stitching" if they aren't explicit polygons
        lines_by_mat = {mat_id: [] for mat_id in set(layer_mapping.values()) if mat_id}

        for layer_name, material_id in layer_mapping.items():
            if not material_id: continue 

            # HATCH
            for hatch in self.msp.query(f'HATCH[layer=="{layer_name}"]'):
                 for loop_poly in self._process_hatch(hatch):
                     if loop_poly.is_valid and not loop_poly.is_empty:
                        raw_polys_by_mat[material_id].append(loop_poly)

            # POLYLINE / LWPOLYLINE
            for entity in self.msp.query(f'*[layer=="{layer_name}"]'):
                poly_points = []
                is_closed = False
                try:
                    if entity.dxftype() == 'LWPOLYLINE':
                        is_closed = entity.closed
                        with entity.points() as pts:
                            for p in pts: poly_points.append((p[0], p[1]))
                    elif entity.dxftype() == 'POLYLINE':
                        is_closed = entity.is_closed
                        for v in entity.vertices: poly_points.append((v.dxf.location.x, v.dxf.location.y))
                    else: continue
                except Exception as e:
                    logging.warning(f"Error reading polyline: {e}")
                    continue
                
                if len(poly_points) >= 3 and is_closed:
                     p = Polygon(poly_points)
                     if p.is_valid: raw_polys_by_mat[material_id].append(p)
                     else: raw_polys_by_mat[material_id].append(p.buffer(0))
                elif len(poly_points) >= 2:
                    # Treat valid open polylines as a series of lines
                    lines_by_mat[material_id].append(LineString(poly_points))

            # LINE
            for line in self.msp.query(f'LINE[layer=="{layer_name}"]'):
                lines_by_mat[material_id].append(LineString([(line.dxf.start.x, line.dxf.start.y), (line.dxf.end.x, line.dxf.end.y)]))
                
            # ARC (Convert to approximated LineStrings)
            for arc in self.msp.query(f'ARC[layer=="{layer_name}"]'):
                pts = self._discretize_arc(
                    (arc.dxf.center.x, arc.dxf.center.y),
                    arc.dxf.radius,
                    arc.dxf.start_angle,
                    arc.dxf.end_angle
                )
                if len(pts) > 1:
                    lines_by_mat[material_id].append(LineString(pts))

        # 2. Process Lines -> Polygons (Stitching)
        for mat_id, lines in lines_by_mat.items():
            if not lines: continue
            
            # Snap endpoints to handle tolerance
            snapped_lines = self._snap_lines(lines, tolerance=0.1) # 0.1 mm tolerance
            
            # Using shapely polygonize
            try:
                # Need to union lines? polygonize expects list of lines.
                # If we have many short segments, polygonize works well.
                
                new_polys = list(polygonize(snapped_lines))
                raw_polys_by_mat[mat_id].extend(new_polys)
            except Exception as e:
                logging.warning(f"Failed to polygonize lines for {mat_id}: {e}")

        # 3. Optimize and Build Scenario
        points = {}
        elements = []
        
        pt_counter = 0
        def add_point(x, y):
            nonlocal pt_counter
            name = f"pt_{pt_counter}"
            points[name] = [round(x, 2), round(y, 2)]
            pt_counter += 1
            return name

        for mat_id, polys in raw_polys_by_mat.items():
            if not polys: continue
            
            # Heal invalid polygons
            valid_polys = []
            for p in polys:
                if not p.is_valid: p = p.buffer(0)
                if p.is_valid and not p.is_empty: valid_polys.append(p)
            
            if not valid_polys: continue

            # Union to merge overlapping fills/hatches
            try:
                temp_merged = unary_union(valid_polys)
                if temp_merged.is_empty: continue
                merged = temp_merged
            except Exception as e:
                logging.error(f"Union failed for {mat_id}: {e}")
                merged = MultiPolygon(valid_polys)
            
            if isinstance(merged, Polygon):
                final_parts = [merged]
            elif isinstance(merged, MultiPolygon):
                final_parts = list(merged.geoms)
            else:
                final_parts = []
                if hasattr(merged, 'geoms'):
                    for g in merged.geoms:
                        if isinstance(g, (Polygon, MultiPolygon)):
                            if isinstance(g, Polygon): final_parts.append(g)
                            else: final_parts.extend(g.geoms)

                
            for part in final_parts:
                if part.area < min_area_threshold: continue
                
                simplified = part.simplify(simplify_tolerance, preserve_topology=True)
                
                if simplified.is_empty: continue
                
                if hasattr(simplified, 'exterior') and simplified.exterior:
                    coords = list(simplified.exterior.coords)
                    if len(coords) < 3: continue
                    if coords[0] == coords[-1]: coords.pop()
                    if len(coords) < 3: continue
                    
                    pt_names = []
                    for x, y in coords:
                        pt_names.append(add_point(x, y))
                        
                    elements.append({
                        "type": "polygon",
                        "name": f"Poly_{mat_id}_{len(elements)}",
                        "material": mat_id,
                        "points": pt_names
                    })

        bounds = self._calculate_bounds(points)
        return {
            "name": "Imported DXF Scenario",
            "description": "Generated from DXF import.",
            "materials": [], 
            "variables": {},
            "boundary_conditions": {
                "convective": {
                    "internal": {"T": 20.0, "R": 0.13},
                    "external": {"T": -5.0, "R": 0.04}
                }
            },
            "points": points,
            "elements": elements,
            "canvas": {
                "bounds": [bounds["x_min"], bounds["x_max"], bounds["y_min"], bounds["y_max"]],
                "grid": bounds["grid"]
            }
        }

    def _process_hatch(self, hatch_entity) -> List[Polygon]:
        """Convert hatch paths to Shapely Polygons. Handles PolylinePath and EdgePath."""
        polys = []
        try:
            for path in hatch_entity.paths:
                vertices = []
                
                path_class = path.__class__.__name__
                
                # 1. PolylinePath
                if path_class == 'PolylinePath':
                    vertices = [(v[0], v[1]) for v in path.vertices]
                    
                # 2. EdgePath (Lines, Arcs, Ellipses)
                elif path_class == 'EdgePath':
                    current_path_pts = []
                    
                    for edge in path.edges:
                        edge_class = edge.__class__.__name__
                        
                        if edge_class == 'LineEdge':
                            s = (edge.start[0], edge.start[1])
                            e = (edge.end[0], edge.end[1])
                            if not current_path_pts: current_path_pts.append(s)
                            current_path_pts.append(e)
                            
                        elif edge_class == 'ArcEdge':
                            pts = self._discretize_arc(
                                (edge.center[0], edge.center[1]),
                                edge.radius,
                                edge.start_angle,
                                edge.end_angle,
                                edge.ccw if hasattr(edge, 'ccw') else True
                            )
                            if current_path_pts and pts:
                                if math.dist(current_path_pts[-1], pts[0]) < 1e-3: pts = pts[1:]
                            current_path_pts.extend(pts)
                            
                        elif edge_class == 'EllipseEdge':
                             pts = self._discretize_ellipse(
                                (edge.center[0], edge.center[1]),
                                (edge.major_axis[0], edge.major_axis[1]),
                                edge.ratio,
                                edge.start_param,
                                edge.end_param
                            )
                             if current_path_pts and pts:
                                if math.dist(current_path_pts[-1], pts[0]) < 1e-3: pts = pts[1:]
                             current_path_pts.extend(pts)
                                
                    vertices = current_path_pts

                # Check if we have a valid loop
                if vertices:
                    if len(vertices) > 1 and math.dist(vertices[0], vertices[-1]) > 1e-3:
                         vertices.append(vertices[0])
                    
                    if len(vertices) >= 4:
                        p = Polygon(vertices)
                        if p.is_valid: polys.append(p)
                        else: polys.append(p.buffer(0))
                            
        except Exception as e:
            logging.warning(f"Error processing hatch: {e}")
            
        return polys

    def _discretize_arc(self, center, radius, start_angle, end_angle, ccw=True, segments=16):
        """Discretize arc into points. Angles in degrees."""
        while start_angle > 360: start_angle -= 360
        while end_angle > 360: end_angle -= 360
        
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        
        if ccw:
            if end_rad <= start_rad: end_rad += 2 * math.pi
        else:
            if start_rad <= end_rad: start_rad += 2 * math.pi
            
        sweep = abs(end_rad - start_rad)
        n = max(3, int(sweep / (2*math.pi) * 32)) 
        
        pts = []
        for i in range(n + 1):
            if ccw: t = start_rad + (sweep * i / n)
            else: t = start_rad - (sweep * i / n) 
                
            x = center[0] + radius * math.cos(t)
            y = center[1] + radius * math.sin(t)
            pts.append((x, y))
            
        return pts
        
    def _discretize_ellipse(self, center, major_axis, ratio, start_param, end_param, segments=16):
        mj_len = math.hypot(major_axis[0], major_axis[1])
        angle_mj = math.atan2(major_axis[1], major_axis[0])
        mn_len = mj_len * ratio
        
        start_t = start_param
        end_t = end_param
        if end_t < start_t: end_t += 2*math.pi
        
        sweep = end_t - start_t
        n = max(3, int(abs(sweep) / (2*math.pi) * 32))
        
        pts = []
        for i in range(n + 1):
            t = start_t + (sweep * i / n)
            ux = mj_len * math.cos(t)
            uy = mn_len * math.sin(t)
            rx = ux * math.cos(angle_mj) - uy * math.sin(angle_mj)
            ry = ux * math.sin(angle_mj) + uy * math.cos(angle_mj)
            pts.append((center[0] + rx, center[1] + ry))
            
        return pts

    def _snap_lines(self, lines: List[LineString], tolerance=0.1) -> List[LineString]:
        """Snap line endpoints to common grid/centroids to ensure connectivity."""
        points = []
        for l in lines:
            points.append(l.coords[0])
            points.append(l.coords[-1])
            
        inv_tol = 1.0 / tolerance
        def get_key(pt):
            return (int(round(pt[0] * inv_tol)), int(round(pt[1] * inv_tol)))
            
        grid = {}
        for p in points:
            k = get_key(p)
            if k not in grid: grid[k] = []
            grid[k].append(p)
            
        replacement = {}
        for k, pts in grid.items():
            if not pts: continue
            avg_x = sum(p[0] for p in pts) / len(pts)
            avg_y = sum(p[1] for p in pts) / len(pts)
            rep = (avg_x, avg_y)
            for p in pts:
                replacement[p] = rep
                
        new_lines = []
        for l in lines:
            start = l.coords[0]
            end = l.coords[-1]
            s_new = replacement.get(start, start)
            e_new = replacement.get(end, end)
            if s_new != e_new:
                new_lines.append(LineString([s_new, e_new]))
                
        return new_lines

    def _calculate_bounds(self, points: Dict[str, List[float]]) -> Dict[str, Any]:
        if not points:
            return {"x_min": 0.0, "x_max": 500.0, "y_min": 0.0, "y_max": 500.0, "grid": 10.0}
            
        xs = [p[0] for p in points.values()]
        ys = [p[1] for p in points.values()]
        
        margin = 100.0
        return {
            "x_min": float(min(xs) - margin),
            "x_max": float(max(xs) + margin),
            "y_min": float(min(ys) - margin),
            "y_max": float(max(ys) + margin),
            "grid": 10.0
        }
