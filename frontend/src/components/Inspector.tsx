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
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Divider from '@mui/material/Divider';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InputAdornment from '@mui/material/InputAdornment';

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
        <Paper
            elevation={0}
            sx={{
                width: 320,
                height: '100%',
                borderLeft: 1,
                borderColor: 'divider',
                overflowY: 'auto',
                backgroundColor: 'background.default',
            }}
        >
            <Box sx={{ p: 2 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                    🔍 Inspector
                </Typography>

                {/* Simulation Controls - Always visible at top */}
                <SimulationControls
                    onRun={onRunSimulation}
                    isRunning={isSimulationRunning}
                    progress={simulationProgress}
                    statusMessage={simulationStatus}
                />

                <Divider sx={{ my: 2 }} />

                {/* Collapsible Sections */}
                <Accordion defaultExpanded disableGutters elevation={0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2">Grid Settings</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <GlobalSettings
                            gridSize={gridSize}
                            onGridSizeChange={onGridSizeChange}
                        />
                    </AccordionDetails>
                </Accordion>

                <Accordion defaultExpanded disableGutters elevation={0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2">Simulation Options</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <SimulationSettings
                            transientEnabled={transientEnabled}
                            onTransientChange={onTransientChange}
                            moldAnalysisEnabled={moldAnalysisEnabled}
                            onMoldAnalysisChange={onMoldAnalysisChange}
                        />
                    </AccordionDetails>
                </Accordion>

                <Accordion disableGutters elevation={0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2">Variables</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        <VariableEditor
                            variables={variables}
                            onUpdateVariable={onUpdateVariable}
                            onAddVariable={onAddVariable}
                        />
                    </AccordionDetails>
                </Accordion>

                <Accordion defaultExpanded disableGutters elevation={0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography variant="subtitle2">Element Properties</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                        {selectedElement && selectedElement.id ? (
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">ID</Typography>
                                    <Typography variant="body2">{selectedElement.id}</Typography>
                                </Box>
                                <Box>
                                    <Typography variant="caption" color="text.secondary">Type</Typography>
                                    <Typography variant="body2">{selectedElement.type}</Typography>
                                </Box>

                                <TextField
                                    label="Material"
                                    value={selectedElement.material || ""}
                                    onChange={(e) => handleUpdate({ material: e.target.value })}
                                    fullWidth
                                />

                                <TextField
                                    label="X"
                                    type="number"
                                    value={selectedElement.simX ?? selectedElement.x}
                                    onChange={(e) => handleUpdate({ simX: parseFloat(e.target.value), x: parseFloat(e.target.value) })}
                                    InputProps={{
                                        endAdornment: <InputAdornment position="end">mm</InputAdornment>,
                                    }}
                                    fullWidth
                                />

                                <TextField
                                    label="Y"
                                    type="number"
                                    value={selectedElement.simY ?? selectedElement.y}
                                    onChange={(e) => handleUpdate({ simY: parseFloat(e.target.value), y: parseFloat(e.target.value) })}
                                    InputProps={{
                                        endAdornment: <InputAdornment position="end">mm</InputAdornment>,
                                    }}
                                    fullWidth
                                />

                                <TextField
                                    label="Width"
                                    type="number"
                                    value={selectedElement.width}
                                    onChange={(e) => handleUpdate({ width: parseFloat(e.target.value) })}
                                    InputProps={{
                                        endAdornment: <InputAdornment position="end">mm</InputAdornment>,
                                    }}
                                    fullWidth
                                />

                                <TextField
                                    label="Height"
                                    type="number"
                                    value={selectedElement.height}
                                    onChange={(e) => handleUpdate({ height: parseFloat(e.target.value) })}
                                    InputProps={{
                                        endAdornment: <InputAdornment position="end">mm</InputAdornment>,
                                    }}
                                    fullWidth
                                />
                            </Box>
                        ) : (
                            <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                                Select an element to view properties.
                            </Typography>
                        )}
                    </AccordionDetails>
                </Accordion>
            </Box>
        </Paper>
    );
};
