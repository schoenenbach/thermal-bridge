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

interface SimulationSettingsProps {
    transientEnabled: boolean;
    onTransientChange: (enabled: boolean) => void;
    moldAnalysisEnabled: boolean;
    onMoldAnalysisChange: (enabled: boolean) => void;
}

export const SimulationSettings: React.FC<SimulationSettingsProps> = ({
    transientEnabled,
    onTransientChange,
    moldAnalysisEnabled,
    onMoldAnalysisChange
}) => {
    return (
        <div className="inspector-section">
            <h4>🌡️ Simulation Settings</h4>
            <div className="inspector-field" style={{ marginBottom: '10px' }}>
                <label style={{ display: 'flex', alignItems: 'center' }}>
                    <input
                        type="checkbox"
                        checked={transientEnabled}
                        onChange={(e) => onTransientChange(e.target.checked)}
                        style={{ marginRight: '8px' }}
                    />
                    Transient Simulation
                </label>
                <small style={{ color: '#666', display: 'block', marginLeft: '20px' }}>
                    Time-dependent heat flow.
                </small>
            </div>

            <div className="inspector-field">
                <label style={{ display: 'flex', alignItems: 'center' }}>
                    <input
                        type="checkbox"
                        checked={moldAnalysisEnabled}
                        onChange={(e) => onMoldAnalysisChange(e.target.checked)}
                        style={{ marginRight: '8px' }}
                    />
                    Mold Analysis
                </label>
                <small style={{ color: '#666', display: 'block', marginLeft: '20px' }}>
                    ISO 13788 risk check.
                </small>
            </div>
        </div>
    );
};
