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
import { ThemeProvider, CssBaseline } from '@mui/material';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Container from '@mui/material/Container';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';

import theme from './theme';
import { ScenarioList } from './components/ScenarioList';
import { ScenarioDetail } from './components/ScenarioDetail';
import GeometryEditor from './components/editor/GeometryEditor';

function App() {
  const [view, setView] = useState<'list' | 'detail' | 'editor'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const handleSelectScenario = (filename: string) => {
    setSelectedScenario(filename);
    setView('detail');
  };

  const handleBack = () => {
    if (view === 'editor') {
      setView('detail');
    } else {
      setSelectedScenario(null);
      setView('list');
    }
  };

  const handleOpenEditor = () => {
    setView('editor');
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AppBar position="static" sx={{ backgroundColor: '#282c34' }}>
          <Toolbar>
            {view !== 'list' && (
              <Button
                color="inherit"
                startIcon={<ArrowBackIcon />}
                onClick={handleBack}
                sx={{ mr: 2 }}
              >
                Back
              </Button>
            )}
            <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
              Thermal Bridge Simulator
            </Typography>
            {view === 'detail' && (
              <Button
                color="inherit"
                startIcon={<EditIcon />}
                onClick={handleOpenEditor}
              >
                Open Editor
              </Button>
            )}
          </Toolbar>
        </AppBar>

        <Container
          maxWidth="xl"
          sx={{
            flexGrow: 1,
            py: 2,
            height: view === 'editor' ? 'calc(100vh - 64px)' : 'auto',
          }}
        >
          {view === 'list' && (
            <ScenarioList onSelectScenario={handleSelectScenario} />
          )}

          {view === 'detail' && selectedScenario && (
            <ScenarioDetail filename={selectedScenario} onBack={handleBack} />
          )}

          {view === 'editor' && selectedScenario && (
            <Box sx={{ height: '100%' }}>
              <GeometryEditor filename={selectedScenario} />
            </Box>
          )}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
