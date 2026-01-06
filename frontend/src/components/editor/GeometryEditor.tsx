/*
 * Copyright (C) 2026 Thomas
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React, { useState, useEffect, useCallback } from 'react';
import StageCanvas from './StageCanvas';
import ShapeFactory from './ShapeFactory';
import { ScenarioElement } from './types';
import { ScenariosService, SimulationService } from '../../api/client';
import { Inspector } from '../Inspector';
import { transformElements } from './transformers';

interface GeometryEditorProps {
    filename: string;
}

const GeometryEditor: React.FC<GeometryEditorProps> = ({ filename }) => {
    const [scale, setScale] = useState(1);
    const [elements, setElements] = useState<ScenarioElement[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [stageHeight, setStageHeight] = useState(600);
    const [gridSize, setGridSize] = useState(10);
    const [transientEnabled, setTransientEnabled] = useState(false);
    const [moldAnalysisEnabled, setMoldAnalysisEnabled] = useState(false);
    const [variables, setVariables] = useState<Record<string, number>>({});
    const [rawScenarioData, setRawScenarioData] = useState<any>(null);

    // Simulation State
    const [isSimRunning, setIsSimRunning] = useState(false);
    const [simProgress, setSimProgress] = useState(0);
    const [simStatus, setSimStatus] = useState("Ready");
    const [simResult, setSimResult] = useState<any>(null);

    // Initial Load
    useEffect(() => {
        setLoading(true);
        ScenariosService.get(filename)
            .then(response => {
                const data = response.data;
                setRawScenarioData(data);

                // Initialize state from data
                if (data.variables) setVariables(data.variables);
                if (data.canvas?.grid) setGridSize(data.canvas.grid);

                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load scenario for editor", err);
                setLoading(false);
            });
    }, [filename]);

    // Reactivity: Recalculate elements when variables or raw data changes
    useEffect(() => {
        if (!rawScenarioData) return;

        const { elements: newElements, stageHeight: newHeight } = transformElements(rawScenarioData, variables);
        setElements(newElements);
        setStageHeight(newHeight);

    }, [rawScenarioData, variables]);


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

    const handleUpdateVariable = (name: string, value: number) => {
        setVariables(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleAddVariable = (name: string, value: number) => {
        setVariables(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleRunSimulation = async () => {
        console.log("Run Simulation Clicked");
        if (!rawScenarioData) {
            console.warn("No scenario data available");
            return;
        }

        setIsSimRunning(true);
        setSimStatus("Initializing...");
        setSimProgress(0);
        setSimResult(null);

        try {
            console.log("Preparing payload...");
            const payload = {
                scenario: {
                    ...rawScenarioData,
                    variables: variables,
                    // Update grid in canvas config
                    canvas: { ...(rawScenarioData.canvas || {}), grid: gridSize }
                },
                use_adaptive_mesh: true,
                override_grid_size: gridSize,
                transient_enabled: transientEnabled,
                mold_analysis: moldAnalysisEnabled,
                indoor_rh: 0.5
            };
            console.log("Sending payload:", payload);

            const response = await SimulationService.runAsync(payload);
            console.log("Simulation Started:", response);
            const { job_id, ws_url } = response;

            // Connect WebSocket
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Construct WebSocket URL correctly
            // ws_url from backend is like /api/ws/simulation/{job_id}
            // We need to prepend host
            const socketUrl = `${wsProtocol}//${window.location.host}${ws_url}`;
            console.log("Connecting WebSocket:", socketUrl);
            const ws = new WebSocket(socketUrl);

            ws.onopen = () => {
                console.log("WebSocket Opened");
                setSimStatus("Connected, waiting for progress...");
            };

            ws.onmessage = (event) => {
                // console.log("WS Message:", event.data);
                try {
                    const data = JSON.parse(event.data);
                    if (data.status === 'progress' || data.percent !== undefined) {
                        setSimProgress(data.percent || 0);
                        setSimStatus(`${data.phase || 'Running'} (${data.step}/${data.total})`);
                    } else if (data.status === 'complete') {
                        console.log("Simulation Complete");
                        setSimProgress(100);
                        setSimStatus("Completed");
                        setSimResult(data.result);
                        setIsSimRunning(false);
                        ws.close();
                    } else if (data.status === 'error') {
                        console.error("Simulation Error:", data.message);
                        setSimStatus(`Error: ${data.message}`);
                        setIsSimRunning(false);
                        ws.close();
                    }
                } catch (e) {
                    console.error("WS Parse Error", e);
                }
            };

            ws.onerror = (e) => {
                console.error("WebSocket error", e);
                setSimStatus("Connection Error (Check Console)");
                setIsSimRunning(false);
            };

        } catch (err: any) {
            console.error("Simulation Start Error", err);
            setSimStatus(`Failed: ${err.message || 'Unknown error'}`);
            setIsSimRunning(false);
        }
    };

    const handleSelect = (id: string) => {
        setSelectedId(id);
    };

    if (loading) return <div>Loading Editor...</div>;

    const selectedElement = elements.find(e => e.id === selectedId) || null;

    return (
        <div style={{ display: 'flex', height: '100vh', flexDirection: 'column' }}>
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                <Inspector
                    selectedElement={selectedElement}
                    onUpdateElement={handleChange}
                    gridSize={gridSize}
                    onGridSizeChange={setGridSize}
                    transientEnabled={transientEnabled}
                    onTransientChange={setTransientEnabled}
                    moldAnalysisEnabled={moldAnalysisEnabled}
                    onMoldAnalysisChange={setMoldAnalysisEnabled}
                    variables={variables}
                    onUpdateVariable={handleUpdateVariable}
                    onAddVariable={handleAddVariable}
                    onRunSimulation={handleRunSimulation}
                    isSimulationRunning={isSimRunning}
                    simulationProgress={simProgress}
                    simulationStatus={simStatus}
                />
                <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ flex: 1 }}>
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
                    {/* Results Panel */}
                    {simResult && (
                        <div style={{
                            height: '250px',
                            borderTop: '1px solid #ccc',
                            padding: '15px',
                            overflowY: 'auto',
                            backgroundColor: '#fff',
                            boxShadow: '0 -2px 10px rgba(0,0,0,0.1)',
                            zIndex: 10
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                <h4 style={{ margin: 0 }}>📊 Simulation Results</h4>
                                <button onClick={() => setSimResult(null)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>✖</button>
                            </div>

                            <div style={{ display: 'flex', gap: '20px' }}>
                                <div style={{ flex: 1 }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9em' }}>
                                        <tbody>
                                            <tr>
                                                <td style={{ fontWeight: 'bold', padding: '5px' }}>Psi-Value:</td>
                                                <td style={{ padding: '5px' }}>{simResult.metrics?.psi_value?.toFixed(4)} W/mK</td>
                                            </tr>
                                            <tr>
                                                <td style={{ fontWeight: 'bold', padding: '5px' }}>fRsi Factor:</td>
                                                <td style={{ padding: '5px' }}>{simResult.metrics?.frsi_factor?.toFixed(3)}</td>
                                            </tr>
                                            <tr>
                                                <td style={{ fontWeight: 'bold', padding: '5px' }}>Min Temp:</td>
                                                <td style={{ padding: '5px' }}>{simResult.metrics?.temp_min?.toFixed(2)} °C</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>

                                {simResult.temperature_map_url && (
                                    <div style={{ display: 'flex', gap: '10px' }}>
                                        <div style={{ textAlign: 'center' }}>
                                            <img src={simResult.temperature_map_url} alt="Temperature Map" style={{ height: '180px', border: '1px solid #eee' }} />
                                            <div style={{ fontSize: '0.8em', color: '#666' }}>Temperature</div>
                                        </div>
                                        {simResult.mold_risk_map_url && (
                                            <div style={{ textAlign: 'center' }}>
                                                <img src={simResult.mold_risk_map_url} alt="Mold Risk" style={{ height: '180px', border: '1px solid #eee' }} />
                                                <div style={{ fontSize: '0.8em', color: '#666' }}>Mold Risk</div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default GeometryEditor;
