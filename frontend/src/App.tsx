import React, { useState } from 'react';
import './App.css';
import { ScenarioList } from './components/ScenarioList';
import { ScenarioDetail } from './components/ScenarioDetail';

function App() {
  const [view, setView] = useState<'list' | 'detail'>('list');
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);

  const handleSelectScenario = (filename: string) => {
    setSelectedScenario(filename);
    setView('detail');
  };

  const handleBack = () => {
    setSelectedScenario(null);
    setView('list');
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

      <main style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {view === 'list' && (
          <ScenarioList onSelectScenario={handleSelectScenario} />
        )}

        {view === 'detail' && selectedScenario && (
          <ScenarioDetail filename={selectedScenario} onBack={handleBack} />
        )}
      </main>
    </div>
  );
}

export default App;
