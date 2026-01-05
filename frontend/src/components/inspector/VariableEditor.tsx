import React, { useState } from 'react';

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
        <div className="inspector-section">
            <h4>📦 Variables</h4>

            {Object.entries(variables).map(([name, value]) => (
                <div key={name} className="inspector-field" style={{ marginBottom: '5px', display: 'flex', alignItems: 'center' }}>
                    <label style={{ flex: 1, fontSize: '0.9em' }}>{name}</label>
                    <input
                        type="number"
                        value={value}
                        onChange={(e) => onUpdateVariable(name, parseFloat(e.target.value))}
                        style={{ width: '80px' }}
                    />
                </div>
            ))}

            <div style={{ marginTop: '10px', display: 'flex', gap: '5px' }}>
                <input
                    type="text"
                    placeholder="Name"
                    value={newVarName}
                    onChange={(e) => setNewVarName(e.target.value)}
                    style={{ flex: 1, minWidth: '0' }}
                />
                <input
                    type="number"
                    value={newVarValue}
                    onChange={(e) => setNewVarValue(parseFloat(e.target.value))}
                    style={{ width: '60px' }}
                />
                <button onClick={handleAdd} disabled={!newVarName}>+</button>
            </div>
        </div>
    );
};
