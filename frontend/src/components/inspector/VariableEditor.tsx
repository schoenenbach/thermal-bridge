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

import React, { useState } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import AddIcon from '@mui/icons-material/Add';
import Stack from '@mui/material/Stack';

interface VariableEditorProps {
    variables: Record<string, number>;
    onUpdateVariable: (name: string, value: number) => void;
    onAddVariable: (name: string, value: number) => void;
}

export const VariableEditor: React.FC<VariableEditorProps> = ({
    variables,
    onUpdateVariable,
    onAddVariable
}) => {
    const [newVarName, setNewVarName] = useState("");
    const [newVarValue, setNewVarValue] = useState(0);

    const handleAdd = () => {
        if (newVarName && !variables.hasOwnProperty(newVarName)) {
            onAddVariable(newVarName, newVarValue);
            setNewVarName("");
            setNewVarValue(0);
        }
    };

    return (
        <Box>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                📦 Variables
            </Typography>

            <Stack spacing={1}>
                {Object.entries(variables).map(([name, value]) => (
                    <Box key={name} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }}>
                            {name}
                        </Typography>
                        <TextField
                            type="number"
                            value={value}
                            onChange={(e) => onUpdateVariable(name, parseFloat(e.target.value))}
                            sx={{ width: 100 }}
                        />
                    </Box>
                ))}
            </Stack>

            <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                <TextField
                    placeholder="Name"
                    value={newVarName}
                    onChange={(e) => setNewVarName(e.target.value)}
                    sx={{ flex: 1 }}
                />
                <TextField
                    type="number"
                    value={newVarValue}
                    onChange={(e) => setNewVarValue(parseFloat(e.target.value))}
                    sx={{ width: 80 }}
                />
                <IconButton
                    onClick={handleAdd}
                    disabled={!newVarName}
                    color="primary"
                    size="small"
                >
                    <AddIcon />
                </IconButton>
            </Stack>
        </Box>
    );
};
