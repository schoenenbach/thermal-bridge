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

interface GlobalSettingsProps {
    gridSize: number;
    onGridSizeChange: (size: number) => void;
}

export const GlobalSettings: React.FC<GlobalSettingsProps> = ({ gridSize, onGridSizeChange }) => {
    return (
        <div className="inspector-section">
            <h4>⚙️ Settings</h4>
            <div className="inspector-field">
                <label>Grid Size (mm)</label>
                <input
                    type="number"
                    value={gridSize}
                    onChange={(e) => onGridSizeChange(parseFloat(e.target.value) || 0)}
                    step="0.5"
                    min="0"
                    style={{ width: '100%' }}
                />
                <small style={{ color: '#666', fontSize: '0.8em' }}>
                    Set {'>'} 0 to override YAML grid.
                </small>
            </div>
        </div>
    );
};
