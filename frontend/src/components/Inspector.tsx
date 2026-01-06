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

import React from 'react';
import { GlobalSettings } from './inspector/GlobalSettings';
import { SimulationSettings } from './inspector/SimulationSettings';
import { VariableEditor } from './inspector/VariableEditor';
import { SimulationControls } from './inspector/SimulationControls';
import { ScenarioElement } from './editor/types';

interface InspectorProps {
    selectedElement: ScenarioElement | null;
    onUpdateElement: (id: string, attrs: any) => void;
    gridSize: number;
    onGridSizeChange: (size: number) => void;
    transientEnabled: boolean;
    onTransientChange: (enabled: boolean) => void;
    moldAnalysisEnabled: boolean;
    onMoldAnalysisChange: (enabled: boolean) => void;
    variables: Record<string, number>;
    onUpdateVariable: (name: string, value: number) => void;
    onAddVariable: (name: string, value: number) => void;
    onRunSimulation: () => void;
    isSimulationRunning: boolean;
    simulationProgress: number;
    simulationStatus: string;
}

export const Inspector: React.FC<InspectorProps> = ({
    selectedElement,
    onUpdateElement,
    gridSize,
    onGridSizeChange,
    transientEnabled,
    onTransientChange,
    moldAnalysisEnabled,
    onMoldAnalysisChange,
    variables,
    onUpdateVariable,
    onAddVariable,
    onRunSimulation,
    isSimulationRunning,
    simulationProgress,
    simulationStatus
}) => {
    const handleUpdate = (attrs: any) => {
        if (selectedElement && selectedElement.id) {
            onUpdateElement(selectedElement.id, attrs);
        }
    };

    return (
        <div style={{
            width: '300px',
            padding: '15px',
            borderLeft: '1px solid #ddd',
            backgroundColor: '#f9f9f9',
            height: '100vh',
            overflowY: 'auto'
        }}>
            <h3 style={{ marginTop: 0 }}>🔍 Inspector</h3>

            <GlobalSettings
                gridSize={gridSize}
                onGridSizeChange={onGridSizeChange}
            />

            <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #eee' }} />

            <SimulationControls
                onRun={onRunSimulation}
                isRunning={isSimulationRunning}
                progress={simulationProgress}
                statusMessage={simulationStatus}
            />

            <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #eee' }} />

            <SimulationSettings
                transientEnabled={transientEnabled}
                onTransientChange={onTransientChange}
                moldAnalysisEnabled={moldAnalysisEnabled}
                onMoldAnalysisChange={onMoldAnalysisChange}
            />

            <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #eee' }} />

            <VariableEditor
                variables={variables}
                onUpdateVariable={onUpdateVariable}
                onAddVariable={onAddVariable}
            />

            <hr style={{ margin: '20px 0', border: 'none', borderTop: '1px solid #eee' }} />

            <div className="inspector-section">
                <h4>Element Properties</h4>
                {selectedElement && selectedElement.id ? (
                    <div>
                        <div style={{ marginBottom: '10px' }}>
                            <strong>ID:</strong> {selectedElement.id}
                        </div>
                        <div style={{ marginBottom: '10px' }}>
                            <strong>Type:</strong> {selectedElement.type}
                        </div>

                        {/* Material Selection - TODO: Fetch from API */}
                        <div className="inspector-field" style={{ marginBottom: '10px' }}>
                            <label style={{ display: 'block', marginBottom: '5px' }}>Material</label>
                            <input
                                type="text"
                                value={selectedElement.material || ""}
                                onChange={(e) => handleUpdate({ material: e.target.value })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="inspector-field" style={{ marginBottom: '10px' }}>
                            <label style={{ display: 'block', marginBottom: '5px' }}>X (mm)</label>
                            <input
                                type="number"
                                value={selectedElement.simX ?? selectedElement.x}
                                onChange={(e) => handleUpdate({ simX: parseFloat(e.target.value), x: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="inspector-field" style={{ marginBottom: '10px' }}>
                            <label style={{ display: 'block', marginBottom: '5px' }}>Y (mm)</label>
                            <input
                                type="number"
                                value={selectedElement.simY ?? selectedElement.y}
                                onChange={(e) => handleUpdate({ simY: parseFloat(e.target.value), y: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="inspector-field" style={{ marginBottom: '10px' }}>
                            <label style={{ display: 'block', marginBottom: '5px' }}>Width (mm)</label>
                            <input
                                type="number"
                                value={selectedElement.width}
                                onChange={(e) => handleUpdate({ width: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="inspector-field" style={{ marginBottom: '10px' }}>
                            <label style={{ display: 'block', marginBottom: '5px' }}>Height (mm)</label>
                            <input
                                type="number"
                                value={selectedElement.height}
                                onChange={(e) => handleUpdate({ height: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>
                    </div>
                ) : (
                    <div style={{ color: '#888', fontStyle: 'italic' }}>
                        Select an element to view properties.
                    </div>
                )}
            </div>
        </div>
    );
};
