import React, { useState, useEffect } from 'react';
import StageCanvas from './StageCanvas';
import ShapeFactory from './ShapeFactory';
import { ScenarioElement } from './types';
import { ScenariosService } from '../../api/client';

interface GeometryEditorProps {
    filename: string;
}

const resolveValue = (val: any, variables: any): number => {
    if (typeof val === 'number') return val;
    if (typeof val === 'string') {
        const match = val.match(/^\$\{(.+)\}$/);
        if (match) {
            const varName = match[1];
            const resolved = variables[varName];
            return typeof resolved === 'number' ? resolved : 0;
        }
        // Try parsing float if it's just a string number
        const parsed = parseFloat(val);
        return isNaN(parsed) ? 0 : parsed;
    }
    return 0;
};

const GeometryEditor: React.FC<GeometryEditorProps> = ({ filename }) => {
    const [scale, setScale] = useState(1);
    const [elements, setElements] = useState<ScenarioElement[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [stageHeight, setStageHeight] = useState(600);

    useEffect(() => {
        setLoading(true);
        ScenariosService.get(filename)
            .then(response => {
                const scenarioData = response.data;
                const variables = scenarioData.variables || {};

                // Get canvas bounds to determine logical height for Y-flipping
                let maxY = 500;
                if (scenarioData.canvas && scenarioData.canvas.bounds) {
                    const bounds = scenarioData.canvas.bounds;
                    const rawMaxY = bounds[3];
                    maxY = resolveValue(rawMaxY, variables) || 500;
                }
                setStageHeight(maxY);

                // Transform API data to Editor Elements
                const loadedElements = (scenarioData.elements || []).map((el: any, index: number) => {
                    const params = el.params || {};
                    const props = { ...el, ...params };

                    // Resolve raw values
                    const rawX = resolveValue(props.x, variables);
                    const rawY = resolveValue(props.y, variables);
                    const w = resolveValue(props.width, variables);
                    const h = resolveValue(props.height, variables);

                    const canvasY = maxY - (rawY + h);

                    // Handle Polygons
                    let calculatedPoints: number[] = [];
                    if (el.type === 'polygon' && el.points && scenarioData.points) {
                        // Map point names to variable-resolved coordinates
                        calculatedPoints = el.points.flatMap((ptName: string) => {
                            const ptDef = scenarioData.points[ptName];
                            if (ptDef) {
                                const ptX = resolveValue(ptDef[0], variables);
                                const ptY = resolveValue(ptDef[1], variables);
                                // Transform Y
                                return [ptX, maxY - ptY];
                            }
                            return [0, 0];
                        });
                    }

                    return {
                        ...el,
                        id: el.id || `el-${index}`,
                        type: el.type,
                        x: rawX,
                        y: canvasY,
                        width: w,
                        height: h,
                        calculatedPoints: calculatedPoints, // For polygons
                        // Store original Sim coords if we want to sync back later
                        simX: rawX,
                        simY: rawY
                    };
                });

                // Filter only supported types
                const supportedElements = loadedElements.filter((el: any) =>
                    ['wall', 'rect', 'polygon', 'window_detail', 'window'].includes(el.type)
                );

                setElements(supportedElements);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load scenario for editor", err);
                setLoading(false);
            });
    }, [filename]);

    const handleWheel = (e: any) => {
        e.evt.preventDefault();
        const scaleBy = 1.05;
        const stage = e.target.getStage();
        const oldScale = stage.scaleX();
        const mousePointTo = {
            x: stage.getPointerPosition().x / oldScale - stage.x() / oldScale,
            y: stage.getPointerPosition().y / oldScale - stage.y() / oldScale,
        };

        const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
        setScale(newScale);

        const newPos = {
            x: -(mousePointTo.x - stage.getPointerPosition().x / newScale) * newScale,
            y: -(mousePointTo.y - stage.getPointerPosition().y / newScale) * newScale,
        };
        stage.position(newPos);
    };

    const handleChange = (id: string, newAttrs: any) => {
        const newElements = elements.map(el => {
            if (el.id === id) {
                return { ...el, ...newAttrs };
            }
            return el;
        });
        setElements(newElements);
    };

    const handleSelect = (id: string) => {
        setSelectedId(id);
    };

    if (loading) return <div>Loading Editor...</div>;

    return (
        <div style={{ display: 'flex', height: '100vh' }}>
            <div style={{ width: '300px', padding: '10px', borderRight: '1px solid #ddd' }}>
                <h3>Inspector</h3>
                {selectedId ? (
                    <div>
                        <p>Selected: {selectedId}</p>
                        <pre style={{ textAlign: 'left', overflow: 'auto' }}>{JSON.stringify(elements.find(e => e.id === selectedId), null, 2)}</pre>
                    </div>
                ) : (
                    <p>Select an element</p>
                )}
                <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
                    <p>Elements matched: {elements.length}</p>
                    <p>Use mouse wheel to zoom/pan.</p>
                </div>
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
                <StageCanvas
                    width={window.innerWidth - 300}
                    height={window.innerHeight}
                    scale={scale}
                    onWheel={handleWheel}
                >
                    {elements.map((el) => (
                        <ShapeFactory
                            key={el.id}
                            element={el}
                            isSelected={el.id === selectedId}
                            onSelect={handleSelect}
                            onChange={handleChange}
                        />
                    ))}
                </StageCanvas>
            </div>
        </div>
    );
};

export default GeometryEditor;
