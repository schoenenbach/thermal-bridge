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
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import InputAdornment from '@mui/material/InputAdornment';

interface GlobalSettingsProps {
    gridSize: number;
    onGridSizeChange: (size: number) => void;
}

export const GlobalSettings: React.FC<GlobalSettingsProps> = ({ gridSize, onGridSizeChange }) => {
    return (
        <Box>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                ⚙️ Settings
            </Typography>
            <TextField
                fullWidth
                label="Grid Size"
                type="number"
                value={gridSize}
                onChange={(e) => onGridSizeChange(parseFloat(e.target.value) || 0)}
                inputProps={{ step: 0.5, min: 0 }}
                InputProps={{
                    endAdornment: <InputAdornment position="end">mm</InputAdornment>,
                }}
                helperText="Set > 0 to override YAML grid."
            />
        </Box>
    );
};
