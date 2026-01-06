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
import './App.css';
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
      setView('detail'); // Back to detail from editor
    } else {
      setSelectedScenario(null);
      setView('list');
    }
  };

  const handleOpenEditor = () => {
    setView('editor');
  };

  return (
    <div className="App">
      <header className="App-header" style={{
        backgroundColor: '#282c34',
        minHeight: '60px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 'calc(10px + 2vmin)',
        color: 'white',
        padding: '20px'
      }}>
        <h1 style={{ margin: 0, fontSize: '24px' }}>Thermal Bridge Simulator</h1>
        <p style={{ margin: '5px 0 0', fontSize: '14px', opacity: 0.8 }}>Frontend Migration (Phase 3A)</p>
      </header>

      <main style={{ maxWidth: '1200px', margin: '0 auto', height: 'calc(100vh - 100px)' }}>
        {view === 'list' && (
          <ScenarioList onSelectScenario={handleSelectScenario} />
        )}

        {view === 'detail' && selectedScenario && (
          <div>
            <button onClick={handleOpenEditor} style={{ marginBottom: '10px' }}>Open Visual Editor</button>
            <ScenarioDetail filename={selectedScenario} onBack={handleBack} />
          </div>
        )}

        {view === 'editor' && (
          <div style={{ height: '100%' }}>
            <button onClick={handleBack} style={{ margin: '10px' }}>Back to Detail</button>
            <GeometryEditor filename={selectedScenario!} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
