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

import { createTheme } from '@mui/material/styles';

/**
 * Custom MUI theme for Thermal Bridge Simulator.
 * - Dark header for professional look
 * - Compact density for engineering tools
 * - Blue primary color matching the simulation visualizations
 */
const theme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#1976d2', // Blue - matches temperature visualization
            dark: '#115293',
            light: '#4791db',
        },
        secondary: {
            main: '#dc004e', // Red - for warnings/heat
        },
        background: {
            default: '#f5f5f5',
            paper: '#ffffff',
        },
    },
    typography: {
        fontFamily: [
            '-apple-system',
            'BlinkMacSystemFont',
            '"Segoe UI"',
            'Roboto',
            '"Helvetica Neue"',
            'Arial',
            'sans-serif',
        ].join(','),
        h1: {
            fontSize: '1.5rem',
            fontWeight: 600,
        },
        h2: {
            fontSize: '1.25rem',
            fontWeight: 600,
        },
        h3: {
            fontSize: '1rem',
            fontWeight: 600,
        },
    },
    components: {
        // Compact density for all inputs
        MuiTextField: {
            defaultProps: {
                size: 'small',
                variant: 'outlined',
            },
        },
        MuiButton: {
            defaultProps: {
                size: 'small',
            },
            styleOverrides: {
                root: {
                    textTransform: 'none', // No uppercase
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 8,
                },
            },
        },
        MuiAccordion: {
            styleOverrides: {
                root: {
                    '&:before': {
                        display: 'none',
                    },
                },
            },
        },
    },
});

export default theme;
