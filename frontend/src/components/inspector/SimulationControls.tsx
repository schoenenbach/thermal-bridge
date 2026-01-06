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

interface SimulationControlsProps {
    onRun: () => void;
    isRunning: boolean;
    progress: number; // 0-100
    statusMessage: string;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
    onRun,
    isRunning,
    progress,
    statusMessage
}) => {
    return (
        <div className="inspector-section">
            <h4>▶️ Simulation</h4>

            <button
                onClick={onRun}
                disabled={isRunning}
                style={{
                    width: '100%',
                    padding: '10px',
                    backgroundColor: isRunning ? '#ccc' : '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: isRunning ? 'not-allowed' : 'pointer',
                    fontWeight: 'bold'
                }}
            >
                {isRunning ? 'Running...' : 'Run Simulation'}
            </button>

            {isRunning && (
                <div style={{ marginTop: '10px' }}>
                    <div style={{
                        height: '6px',
                        width: '100%',
                        backgroundColor: '#eee',
                        borderRadius: '3px',
                        overflow: 'hidden'
                    }}>
                        <div style={{
                            height: '100%',
                            width: `${progress}%`,
                            backgroundColor: '#2196F3',
                            transition: 'width 0.3s ease'
                        }} />
                    </div>
                    <small style={{ display: 'block', marginTop: '5px', color: '#666', textAlign: 'center' }}>
                        {statusMessage} ({Math.round(progress)}%)
                    </small>
                </div>
            )}
        </div>
    );
};
