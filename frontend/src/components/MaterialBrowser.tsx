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

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';

import { MaterialsService } from '../api/client';
import { MaterialInfo } from '../api/models';

const MaterialBrowser: React.FC = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('');

    // Fetch materials
    const { data: materials, isLoading, error } = useQuery({
        queryKey: ['materials'],
        queryFn: MaterialsService.list,
    });

    // Fetch categories
    const { data: categories } = useQuery({
        queryKey: ['materialCategories'],
        queryFn: MaterialsService.listCategories,
    });

    // Filter materials based on search and category
    const filteredMaterials = useMemo(() => {
        if (!materials) return [];

        return materials.filter((mat: MaterialInfo) => {
            const matchesSearch = searchTerm === '' ||
                mat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                mat.id.toLowerCase().includes(searchTerm.toLowerCase());

            const matchesCategory = selectedCategory === '' ||
                mat.category === selectedCategory;

            return matchesSearch && matchesCategory;
        });
    }, [materials, searchTerm, selectedCategory]);

    const handleCategoryChange = (event: SelectChangeEvent<string>) => {
        setSelectedCategory(event.target.value);
    };

    if (isLoading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Alert severity="error" sx={{ m: 2 }}>
                Failed to load materials. Please check that the backend API is running.
            </Alert>
        );
    }

    return (
        <Box sx={{ p: 2 }}>
            <Typography variant="h5" gutterBottom>
                Material Library
            </Typography>

            {/* Filters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                <TextField
                    placeholder="Search materials..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    size="small"
                    sx={{ width: 300 }}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon />
                            </InputAdornment>
                        ),
                    }}
                />

                <FormControl size="small" sx={{ minWidth: 200 }}>
                    <InputLabel>Category</InputLabel>
                    <Select
                        value={selectedCategory}
                        onChange={handleCategoryChange}
                        label="Category"
                    >
                        <MenuItem value="">
                            <em>All Categories</em>
                        </MenuItem>
                        {categories?.map((cat: string) => (
                            <MenuItem key={cat} value={cat}>
                                {cat}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>

                <Typography variant="body2" color="text.secondary" sx={{ alignSelf: 'center' }}>
                    {filteredMaterials.length} material{filteredMaterials.length !== 1 ? 's' : ''} found
                </Typography>
            </Box>

            {/* Material Grid */}
            <Grid container spacing={2}>
                {filteredMaterials.map((material: MaterialInfo) => (
                    <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={material.id}>
                        <Card
                            variant="outlined"
                            sx={{
                                height: '100%',
                                transition: 'box-shadow 0.2s',
                                '&:hover': {
                                    boxShadow: 3,
                                }
                            }}
                        >
                            <CardContent>
                                {/* Color Swatch */}
                                <Box
                                    sx={{
                                        width: '100%',
                                        height: 8,
                                        backgroundColor: material.color || '#808080',
                                        borderRadius: 1,
                                        mb: 1.5,
                                    }}
                                />

                                <Typography variant="subtitle1" fontWeight="medium" noWrap>
                                    {material.name}
                                </Typography>

                                <Typography variant="body2" color="text.secondary" gutterBottom>
                                    λ = {material.lambda.toFixed(3)} W/mK
                                </Typography>

                                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 1 }}>
                                    {material.category && (
                                        <Chip
                                            label={material.category}
                                            size="small"
                                            variant="outlined"
                                        />
                                    )}
                                </Box>

                                {material.source && (
                                    <Typography
                                        variant="caption"
                                        color="text.secondary"
                                        sx={{ display: 'block', mt: 1 }}
                                    >
                                        {material.source}
                                    </Typography>
                                )}
                            </CardContent>
                        </Card>
                    </Grid>
                ))}
            </Grid>

            {filteredMaterials.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography color="text.secondary">
                        No materials match your search criteria.
                    </Typography>
                </Box>
            )}
        </Box>
    );
};

export default MaterialBrowser;
