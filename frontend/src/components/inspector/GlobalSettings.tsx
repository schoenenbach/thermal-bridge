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
