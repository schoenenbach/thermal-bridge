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
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';

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

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return <Alert severity="error">{error}</Alert>;
    }

    if (!detail) {
        return <Alert severity="warning">No data available</Alert>;
    }

    return (
        <Box sx={{ py: 2 }}>
            <Typography variant="h5" component="h2" sx={{ mb: 3 }}>
                {detail.data.name || detail.filename}
            </Typography>

            <Box sx={{ display: 'flex', gap: 3, height: 'calc(100vh - 200px)' }}>
                {/* YAML Editor */}
                <Paper sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column' }}>
                    <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
                        YAML Content
                    </Typography>
                    <TextField
                        fullWidth
                        multiline
                        value={detail.yaml_content}
                        InputProps={{ readOnly: true }}
                        sx={{
                            flex: 1,
                            '& .MuiInputBase-root': {
                                fontFamily: 'monospace',
                                fontSize: '0.875rem',
                                height: '100%',
                                alignItems: 'flex-start',
                            },
                            '& .MuiInputBase-input': {
                                height: '100% !important',
                                overflow: 'auto !important',
                            },
                        }}
                    />
                </Paper>

                {/* Preview Panel */}
                <Paper
                    sx={{
                        flex: 1,
                        p: 2,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: '#f0f8ff',
                    }}
                >
                    <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
                        Preview
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Click "Open Editor" in the toolbar to view and edit the geometry.
                    </Typography>
                </Paper>
            </Box>
        </Box>
    );
};
