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
import Button from '@mui/material/Button';
import LinearProgress from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import HourglassTopIcon from '@mui/icons-material/HourglassTop';

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
        <Box>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                ▶️ Simulation
            </Typography>

            <Button
                fullWidth
                variant="contained"
                color={isRunning ? 'inherit' : 'success'}
                onClick={onRun}
                disabled={isRunning}
                startIcon={isRunning ? <HourglassTopIcon /> : <PlayArrowIcon />}
            >
                {isRunning ? 'Running...' : 'Run Simulation'}
            </Button>

            {isRunning && (
                <Box sx={{ mt: 2 }}>
                    <LinearProgress
                        variant="determinate"
                        value={progress}
                        sx={{ height: 8, borderRadius: 4 }}
                    />
                    <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ display: 'block', mt: 0.5, textAlign: 'center' }}
                    >
                        {statusMessage} ({Math.round(progress)}%)
                    </Typography>
                </Box>
            )}
        </Box>
    );
};
