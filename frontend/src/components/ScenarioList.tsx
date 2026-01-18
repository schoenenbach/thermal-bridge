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
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardActionArea from '@mui/material/CardActionArea';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import LayersIcon from '@mui/icons-material/Layers';
import StraightenIcon from '@mui/icons-material/Straighten';

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

    return (
        <Box>
            <Typography variant="h5" component="h2" sx={{ mb: 3 }}>
                Available Scenarios
            </Typography>
            <Box sx={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: 2
            }}>
                {scenarios.map(scenario => (
                    <Card elevation={2} key={scenario.filename}>
                        <CardActionArea onClick={() => onSelectScenario(scenario.filename)}>
                            <CardContent>
                                <Typography variant="h6" component="h3" gutterBottom>
                                    {scenario.name}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    {scenario.filename}
                                </Typography>
                                {scenario.description && (
                                    <Typography variant="body2" sx={{ mt: 1 }}>
                                        {scenario.description}
                                    </Typography>
                                )}
                                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                                    <Chip
                                        icon={<LayersIcon />}
                                        label={`${scenario.element_count} elements`}
                                        size="small"
                                        variant="outlined"
                                    />
                                    {scenario.has_measurements && (
                                        <Chip
                                            icon={<StraightenIcon />}
                                            label="Measurements"
                                            size="small"
                                            color="primary"
                                            variant="outlined"
                                        />
                                    )}
                                </Box>
                            </CardContent>
                        </CardActionArea>
                    </Card>
                ))}
            </Box>
        </Box>
    );
};
