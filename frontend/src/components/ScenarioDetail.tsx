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
import { ScenarioDetail as ScenarioDetailType } from '../api/models';

interface ScenarioDetailProps {
    filename: string;
    onBack: () => void;
}

export const ScenarioDetail: React.FC<ScenarioDetailProps> = ({ filename, onBack }) => {
    const [detail, setDetail] = useState<ScenarioDetailType | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        ScenariosService.get(filename)
            .then(data => {
                setDetail(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load scenario detail", err);
                setError(`Failed to load scenario '${filename}'`);
                setLoading(false);
            });
    }, [filename]);

    if (loading) return <div>Loading details...</div>;
    if (error) return <div style={{ color: 'red' }}>
        {error} <br />
        <button onClick={onBack}>Back to List</button>
    </div>;
    if (!detail) return <div>No data</div>;

    return (
        <div style={{ padding: '20px' }}>
            <button onClick={onBack} style={{ marginBottom: '20px' }}>&larr; Back to List</button>

            <h2>{detail.data.name || detail.filename}</h2>

            <div style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 150px)' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <h3>YAML Content</h3>
                    <textarea
                        readOnly
                        value={detail.yaml_content}
                        style={{
                            flex: 1,
                            fontFamily: 'monospace',
                            padding: '10px',
                            backgroundColor: '#f5f5f5',
                            border: '1px solid #ccc'
                        }}
                    />
                </div>

                <div style={{ flex: 1 }}>
                    <h3>Preview</h3>
                    <div style={{
                        padding: '20px',
                        border: '1px solid #dashed',
                        backgroundColor: '#f0f8ff',
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <p>Click "Open Visual Editor" above to view and edit the geometry.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
