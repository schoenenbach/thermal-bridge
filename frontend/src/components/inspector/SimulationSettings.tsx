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
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import Typography from '@mui/material/Typography';

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
        <Box>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                🌡️ Simulation Settings
            </Typography>

            <FormControlLabel
                control={
                    <Checkbox
                        checked={transientEnabled}
                        onChange={(e) => onTransientChange(e.target.checked)}
                        size="small"
                    />
                }
                label={
                    <Box>
                        <Typography variant="body2">Transient Simulation</Typography>
                        <Typography variant="caption" color="text.secondary">
                            Time-dependent heat flow.
                        </Typography>
                    </Box>
                }
                sx={{ alignItems: 'flex-start', mb: 1 }}
            />

            <FormControlLabel
                control={
                    <Checkbox
                        checked={moldAnalysisEnabled}
                        onChange={(e) => onMoldAnalysisChange(e.target.checked)}
                        size="small"
                    />
                }
                label={
                    <Box>
                        <Typography variant="body2">Mold Analysis</Typography>
                        <Typography variant="caption" color="text.secondary">
                            ISO 13788 risk check.
                        </Typography>
                    </Box>
                }
                sx={{ alignItems: 'flex-start' }}
            />
        </Box>
    );
};
