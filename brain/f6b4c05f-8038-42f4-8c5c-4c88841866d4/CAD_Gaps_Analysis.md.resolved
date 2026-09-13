# CAD/Design View - Gap Analysis

## Current State ✅

**Implemented Features:**
1. ✅ 3D visualization with Plotly
2. ✅ Individual module rendering
3. ✅ Dynamic shadows based on sun position
4. ✅ Terrain/slope modeling
5. ✅ Environmental elements (trees, fence, roads, inverter station)
6. ✅ Racking structure (piles + torque tubes)
7. ✅ eBOS visualization (cable trays, combiners)
8. ✅ Ground clearance adjustable
9. ✅ GCR calculation
10. ✅ Row spacing optimization

---

## Identified Gaps (12 Total)

### High Priority (Must-Have for Professional CAD)

**#1: DXF/DWG Export**
- **Current**: Only interactive Plotly view
- **Need**: Export to AutoCAD format
- **Use Case**: Share with architects, civil engineers, permitting
- **Effort**: 2-3 days (using `ezdxf` library)
- **Impact**: HIGH - Required for professional workflows

**#2: Dimensions & Annotations**
- **Current**: No measurement tools
- **Need**: Distance measurements, area calculations, labels
- **Use Case**: Quick design verification, client presentations
- **Effort**: 4-6 hours
- **Impact**: HIGH - Essential for design review

**#3: Setback Compliance Visualization**
- **Current**: No boundary/setback overlay
- **Need**: Property lines, setbacks, exclusion zones
- **Use Case**: Zoning compliance, permitting
- **Effort**: 1-2 days
- **Impact**: HIGH - Avoid permitting rejections

### Medium Priority (Aurora Solar Features)

**#4: Roof Module Placement**
- **Current**: Only ground-mount
- **Need**: Rooftop design with azimuth faces
- **Use Case**: Commercial/residential rooftop
- **Effort**: 1 week (complex geometry)
- **Impact**: MEDIUM - Opens new market segment

**#5: Shade Report Integration**
- **Current**: Static shadows at one time
- **Need**: Annual shading analysis overlay
- **Use Case**: Show shading losses on CAD
- **Effort**: 2-3 days
- **Impact**: MEDIUM - Better design decisions

**#6: Module-Level Data Overlay**
- **Current**: All modules look identical
- **Need**: Color-code by: production, shading, defects
- **Use Case**: Identify underperforming areas
- **Effort**: 1 day
- **Impact**: MEDIUM - O&M value

**#7: Interactive Layer Control**
- **Current**: All traces shown always
- **Need**: Toggle layers (modules, racking, shadows, env)
- **Use Case**: Focus on specific design elements
- **Effort**: 4-6 hours
- **Impact**: MEDIUM - User experience

### Advanced Features (Nice-to-Have)

**#8: BIM Integration**
- **Current**: Standalone 3D view
- **Need**: Export to Revit/IFC format
- **Use Case**: Integrate with building models
- **Effort**: 1-2 weeks
- **Impact**: LOW - Niche use case

**#9: Drone Imagery Underlay**
- **Current**: Synthetic ground texture
- **Need**: Import georeferenced drone photos
- **Use Case**: Site-accurate visualization
- **Effort**: 2-3 days
- **Impact**: MEDIUM - Client wow factor

**#10: Wind Load Visualization**
- **Current**: No structural analysis
- **Need**: Show wind pressure zones
- **Use Case**: Racking design verification
- **Effort**: 3-4 days
- **Impact**: LOW - Edge case

**#11: Time-Lapse Sun Path**
- **Current**: Static sun position
- **Need**: Animate sun path through day/year
- **Use Case**: Shading analysis presentation
- **Effort**: 1 day
- **Impact**: MEDIUM - Sales tool

**#12: ML-Optimized Layout**
- **Current**: Manual pitch/spacing
- **Need**: AI-suggested optimal configuration
- **Use Case**: Maximize yield with constraints
- **Effort**: 1-2 weeks
- **Impact**: HIGH - Competitive advantage

---

## Prioritized Roadmap

### Phase 1: Professional Essentials (1-2 weeks)
1. DXF Export (#1)
2. Dimensions & Annotations (#2)
3. Setback Compliance (#3)

### Phase 2: Aurora Solar Parity (2-3 weeks)
4. Roof Module Placement (#4)
5. Shade Report Integration (#5)
6. Interactive Layers (#7)

### Phase 3: Differentiation (1 month)
7. Module-Level Data Overlay (#6)
8. Drone Imagery Underlay (#9)
9. Time-Lapse Sun Path (#11)
10. ML-Optimized Layout (#12)

### Phase 4: Enterprise (Future)
11. BIM Integration (#8)
12. Wind Load Visualization (#10)

---

## Quick Wins (What We Can Do Today)

### ✅ Quick Enhancement #1: Layer Toggle
```python
# Add to app.py Design tab
layer_cols = st.columns(5)
show_modules = layer_cols[0].checkbox("Modules", True)
show_racking = layer_cols[1].checkbox("Racking", True)
show_shadows = layer_cols[2].checkbox("Shadows", True)
show_environment = layer_cols[3].checkbox("Environment", True)
show_ebos = layer_cols[4].checkbox("eBOS", True)
```

### ✅ Quick Enhancement #2: Measurement Tool
```python
st.markdown(\"\"\"
**Site Metrics**:
- Total Array Area: {array_area:.0f} m²
- Land Area Required: {land_area:.0f} m² ({land_area/4047:.1f} acres)
- Perimeter Fence: {perimeter:.0f} m
\"\"\")
```

### ✅ Quick Enhancement #3: Export as Image
```python
# Already available via Plotly camera icon
# Just add instructions:
st.info("💡 Tip: Click camera icon to save as PNG for presentations")
```

---

## Comparison: SolarEPC-Pro vs. Aurora Solar CAD

| Feature | SolarEPC-Pro | Aurora Solar | Gap |
|---------|--------------|--------------|-----|
| 3D Visualization | ✅ | ✅ | None |
| Ground-mount | ✅ | ✅ | None  |
| Rooftop | ❌ | ✅ | **#4** |
| Shadows | ✅ Static | ✅ Animated | **#11** |
| DXF Export | ❌ | ✅ | **#1** |
| Setbacks | ❌ | ✅ | **#3** |
| Dimensions | ❌ | ✅ | **#2** |
| Drone Photos | ❌ | ✅ | **#9** |
| BIM Export | ❌ | ✅ | **#8** |
| ML Optimization | ❌ | ✅ | **#12** |

**Current Score**: 3/10 Aurora  features  
**After Phase 1**: 6/10 features  
**After Phase 2**: 9/10 features

---

## Recommended Next Steps

**For Immediate Impact**:
1. Implement layer toggle (30 min)
2. Add measurement overlays (2 hours)
3. Add image export instructions (5 min)

**For Professional Deployment**:
1. DXF Export (#1) - 2-3 days
2. Setback zones (#3) - 1 day
3. Dimensions (#2) - 1 day

**Total Phase 1**: 4-5 days of work for production-ready CAD

---

## Summary

**Current CAD Capabilities**: 8/10 (excellent 3D, lacks file interop)  
**vs. Aurora Solar**: 3/10 feature parity  
**Biggest Gaps**: DXF export, setbacks, roof support  
**Quick Wins Available**: Yes (layer toggle, measurements)  
**Recommended Investment**: Phase 1 (1-2 weeks) = Professional-grade
