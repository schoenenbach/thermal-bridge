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

import React, { useEffect, useState } from 'react';
import { ScenariosService } from '../api/client';
import { ScenarioSummary } from '../api/models';

interface ScenarioListProps {
    onSelectScenario: (filename: string) => void;
}

export const ScenarioList: React.FC<ScenarioListProps> = ({ onSelectScenario }) => {
    const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        ScenariosService.list()
            .then(data => {
                setScenarios(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load scenarios", err);
                setError("Failed to load scenarios. Ensure backend is running.");
                setLoading(false);
            });
    }, []);

    if (loading) return <div>Loading scenarios...</div>;
    if (error) return <div style={{ color: 'red' }}>{error}</div>;

    return (
        <div style={{ padding: '20px' }}>
            <h2>Available Scenarios</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {scenarios.map(scenario => (
                    <div
                        key={scenario.filename}
                        style={{
                            border: '1px solid #ddd',
                            padding: '15px',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            backgroundColor: '#fff',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                        }}
                        onClick={() => onSelectScenario(scenario.filename)}
                    >
                        <h3 style={{ margin: '0 0 10px 0' }}>{scenario.name}</h3>
                        <p style={{ fontSize: '0.9em', color: '#666' }}>{scenario.filename}</p>
                        {scenario.description && <p>{scenario.description}</p>}
                        <div style={{ fontSize: '0.85em', marginTop: '10px', color: '#888' }}>
                            Elements: {scenario.element_count} | Measurements: {scenario.has_measurements ? 'Yes' : 'No'}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
